from datetime import timedelta
from decimal import Decimal
from io import BytesIO
import secrets

from django.http import HttpResponse

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from accounts.models import UserNotification
from accounts.permissions import IsAdmin
from tenancy.access import HasRequiredFeature, request_company

from .models import (
    EmployeePenalty,
    EmployeeProfile,
    EmployeeTrainingAssignment,
    TrainingCourse,
    TrainingLesson,
    TrainingQuestion,
    TrainingTrainerReview,
    TrainingCertificate,
)


def _notify(user, event_key, title, message, priority="NORMAL", metadata=None):
    if not user or not user.is_active:
        return
    UserNotification.objects.update_or_create(
        user=user,
        event_key=event_key,
        defaults={
            "title": title[:140],
            "message": message[:1000],
            "category": "HRMS",
            "priority": priority,
            "action": "NONE",
            "metadata": metadata or {},
        },
    )


def _eligible(course, employee):
    return course.audience == "ALL" or course.audience == employee.designation


def _courses_for_employee(employee):
    rows = TrainingCourse.objects.filter(
        is_active=True,
        is_published=True,
        is_mandatory=True,
    )
    if employee.company_id:
        rows = rows.filter(company_id=employee.company_id)
    else:
        rows = rows.filter(company__isnull=True)
    return rows


def sync_training_assignments(employee):
    today = timezone.localdate()
    for course in _courses_for_employee(employee):
        if not _eligible(course, employee):
            continue
        assignment, _ = EmployeeTrainingAssignment.objects.get_or_create(
            employee=employee,
            course=course,
            defaults={
                "due_date": today + timedelta(days=course.due_days),
                "grace_until": today + timedelta(days=course.due_days + course.grace_days),
            },
        )
        enforce_assignment(assignment)
    return EmployeeTrainingAssignment.objects.filter(employee=employee).select_related("course", "penalty")


def enforce_assignment(assignment):
    if assignment.status == "COMPLETED":
        return assignment

    today = timezone.localdate()
    changed = []

    if today > assignment.due_date and assignment.status != "OVERDUE":
        assignment.status = "OVERDUE"
        assignment.compliance_strike = True
        changed.extend(["status", "compliance_strike"])
        _notify(
            assignment.employee.user,
            f"training-overdue:{assignment.id}",
            "Mandatory training overdue",
            (
                f"{assignment.course.title} was due on {assignment.due_date:%d %b %Y}. "
                f"Complete the lessons and pass the quiz now. Grace period ends "
                f"{assignment.grace_until:%d %b %Y}."
            ),
            priority="CRITICAL",
            metadata={"assignment_id": assignment.id, "course_id": assignment.course_id},
        )
        manager = assignment.employee.reporting_manager
        if manager:
            _notify(
                manager.user,
                f"training-escalation:{assignment.id}",
                "Team training overdue",
                f"{assignment.employee.user.get_full_name() or assignment.employee.employee_id} has overdue mandatory training.",
                priority="HIGH",
                metadata={"assignment_id": assignment.id, "employee_id": assignment.employee_id},
            )
        _notify(
            assignment.course.created_by,
            f"training-admin-escalation:{assignment.id}",
            "Mandatory training overdue",
            f"{assignment.employee.user.get_full_name() or assignment.employee.employee_id} has not completed {assignment.course.title}.",
            priority="HIGH",
            metadata={"assignment_id": assignment.id, "employee_id": assignment.employee_id},
        )

    days_left = (assignment.due_date - today).days
    if 0 <= days_left <= 2:
        _notify(
            assignment.employee.user,
            f"training-due:{assignment.id}:{today.isoformat()}",
            "Mandatory training due soon",
            (
                f"{assignment.course.title} is due in {days_left} day"
                f"{'' if days_left == 1 else 's'}. Passing score: {assignment.course.passing_score}%."
            ),
            priority="HIGH",
            metadata={"assignment_id": assignment.id, "course_id": assignment.course_id},
        )

    if today > assignment.grace_until and not assignment.penalty_created:
        creator = assignment.course.created_by
        if creator and creator.is_active and Decimal(assignment.course.penalty_amount) > 0:
            penalty = EmployeePenalty.objects.create(
                employee=assignment.employee,
                penalty_date=today,
                amount=assignment.course.penalty_amount,
                reason=(
                    f"Mandatory training overdue after grace period: "
                    f"{assignment.course.title}. Auto-generated as DRAFT; "
                    f"Admin approval required before payroll deduction."
                ),
                status="DRAFT",
                created_by=creator,
            )
            assignment.penalty = penalty
            assignment.penalty_created = True
            changed.extend(["penalty", "penalty_created"])
            _notify(
                assignment.employee.user,
                f"training-penalty-draft:{assignment.id}",
                "Training compliance penalty pending review",
                (
                    f"A ₹{assignment.course.penalty_amount} penalty draft was created because "
                    f"{assignment.course.title} remained incomplete after the grace period. "
                    f"Admin must review it before any payroll deduction."
                ),
                priority="CRITICAL",
                metadata={"assignment_id": assignment.id, "penalty_id": penalty.id},
            )
            _notify(
                creator,
                f"training-penalty-review:{assignment.id}",
                "Training penalty requires Admin review",
                (
                    f"Review the ₹{assignment.course.penalty_amount} draft penalty for "
                    f"{assignment.employee.user.get_full_name() or assignment.employee.employee_id}."
                ),
                priority="HIGH",
                metadata={"assignment_id": assignment.id, "penalty_id": penalty.id},
            )

    if changed:
        assignment.save(update_fields=list(dict.fromkeys(changed)))
    return assignment



def _trainer_average(row):
    reviews = list(row.trainer_reviews.all())
    if not reviews:
        return Decimal("0.00")
    total = sum(
        review.behaviour_score + review.communication_score + review.knowledge_score
        for review in reviews
    )
    return Decimal(total) / Decimal(len(reviews) * 3)


def _certificate_payload(row):
    certificate = getattr(row, "certificate", None)
    lesson_count = row.course.lessons.count()
    completed_count = len({int(v) for v in (row.lessons_completed or [])})
    reviews_count = row.trainer_reviews.count()
    trainer_average = _trainer_average(row)
    all_lessons_complete = lesson_count > 0 and completed_count >= lesson_count
    quiz_passed = row.quiz_score >= row.course.passing_score
    required_reviews = min(int(row.course.required_trainer_reviews or 0), lesson_count)
    trainer_reviews_complete = reviews_count >= required_reviews
    minimum_trainer_average = Decimal(row.course.minimum_trainer_average or 0)
    trainer_standard_met = (
        required_reviews == 0
        or (trainer_reviews_complete and trainer_average >= minimum_trainer_average)
    )
    eligible = (
        row.course.certificate_enabled
        and row.status == "COMPLETED"
        and all_lessons_complete
        and quiz_passed
        and trainer_standard_met
    )
    payload = {
        "eligible": eligible,
        "requirements": {
            "lessons_complete": all_lessons_complete,
            "quiz_passed": quiz_passed,
            "trainer_reviews_complete": trainer_reviews_complete,
            "trainer_standard_met": trainer_standard_met,
            "required_reviews": required_reviews,
            "reviews_received": reviews_count,
            "minimum_trainer_average": float(minimum_trainer_average),
            "trainer_average": float(round(trainer_average, 2)),
        },
        "certificate_enabled": row.course.certificate_enabled,
        "issued": certificate is not None,
    }
    if certificate is not None:
        expired = timezone.localdate() > certificate.valid_until
        revoked = certificate.revoked_at is not None
        payload["certificate"] = {
            "certificate_number": certificate.certificate_number,
            "verification_code": certificate.verification_code,
            "employee_name": row.employee.user.get_full_name() or row.employee.user.phone,
            "employee_code": row.employee.employee_id,
            "course_title": row.course.title,
            "quiz_score": certificate.quiz_score,
            "trainer_average": float(certificate.trainer_average),
            "final_score": float(certificate.final_score),
            "issued_at": certificate.issued_at.isoformat(),
            "valid_until": certificate.valid_until.isoformat(),
            "status": "REVOKED" if revoked else ("EXPIRED" if expired else "VALID"),
            "revoke_reason": certificate.revoke_reason,
            "pdf_path": f"/employees/hrms/training/certificates/{certificate.verification_code}/pdf/",
        }
    return payload


def _assignment_payload(row, include_content=False):
    course = row.course
    lessons = list(course.lessons.all())
    completed_ids = {int(v) for v in (row.lessons_completed or [])}
    payload = {
        "id": row.id,
        "course_id": course.id,
        "title": course.title,
        "description": course.description,
        "mandatory": course.is_mandatory,
        "audience": course.audience,
        "passing_score": course.passing_score,
        "certificate_enabled": course.certificate_enabled,
        "required_trainer_reviews": course.required_trainer_reviews,
        "minimum_trainer_average": float(course.minimum_trainer_average),
        "due_date": row.due_date.isoformat(),
        "grace_until": row.grace_until.isoformat(),
        "status": row.status,
        "quiz_score": row.quiz_score,
        "attempts": row.attempts,
        "compliance_strike": row.compliance_strike,
        "penalty_created": row.penalty_created,
        "penalty_id": row.penalty_id,
        "lesson_count": len(lessons),
        "lessons_completed_count": len(completed_ids),
        "progress_percent": round((len(completed_ids) / len(lessons) * 100) if lessons else 0),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "planned_days": course.lessons.values("day_number").distinct().count(),
        "planned_minutes": sum(lesson.duration_minutes for lesson in lessons),
        "trainer_reviews_count": row.trainer_reviews.count(),
        "certification": _certificate_payload(row),
    }
    if include_content:
        payload["lessons"] = [
            {
                "id": lesson.id,
                "order": lesson.order,
                "title": lesson.title,
                "content": lesson.content,
                "key_takeaway": lesson.key_takeaway,
                "video_asset": lesson.video_asset,
                "video_url": lesson.video_url,
                "resource_url": lesson.resource_url,
                "resource_label": lesson.resource_label,
                "day_number": lesson.day_number,
                "duration_minutes": lesson.duration_minutes,
                "trainer_script": lesson.trainer_script,
                "practice_task": lesson.practice_task,
                "trainer_review": next(({
                    "behaviour_score": review.behaviour_score,
                    "communication_score": review.communication_score,
                    "knowledge_score": review.knowledge_score,
                    "strengths": review.strengths,
                    "gaps": review.gaps,
                    "coaching_action": review.coaching_action,
                    "notes": review.notes,
                    "trainer_name": review.trainer.get_full_name() or review.trainer.phone,
                    "reviewed_at": review.reviewed_at.isoformat(),
                } for review in row.trainer_reviews.all() if review.lesson_id == lesson.id), None),
                "completed": lesson.id in completed_ids,
            }
            for lesson in lessons
        ]
        payload["questions"] = [
            {
                "id": question.id,
                "order": question.order,
                "question": question.question,
                "options": {
                    "A": question.option_a,
                    "B": question.option_b,
                    "C": question.option_c,
                    "D": question.option_d,
                },
            }
            for question in course.questions.all()
        ]
    return payload


class TrainingListAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "training"

    def get(self, request):
        role = str(getattr(request.user, "role", "")).upper()
        if role == "ADMIN":
            company = request_company(request)
            employees = EmployeeProfile.objects.filter(is_active=True)
            if company is not None:
                employees = employees.filter(company=company)
            else:
                employees = employees.filter(company__isnull=True)
            for employee in employees:
                sync_training_assignments(employee)
            rows = EmployeeTrainingAssignment.objects.select_related(
                "employee__user", "course", "penalty"
            )
            if company is not None:
                rows = rows.filter(employee__company=company)
            else:
                rows = rows.filter(employee__company__isnull=True)
            rows = rows.order_by("status", "due_date", "employee__employee_id")
            today = timezone.localdate()
            for row in rows:
                enforce_assignment(row)
            rows = list(rows)
            return Response({
                "scope": "ADMIN",
                "summary": {
                    "total": len(rows),
                    "completed": sum(1 for r in rows if r.status == "COMPLETED"),
                    "overdue": sum(1 for r in rows if r.status == "OVERDUE"),
                    "pending_penalty_review": sum(
                        1 for r in rows
                        if r.penalty_id and getattr(r.penalty, "status", "") == "DRAFT"
                    ),
                    "due_next_2_days": sum(
                        1 for r in rows
                        if r.status != "COMPLETED" and 0 <= (r.due_date - today).days <= 2
                    ),
                },
                "assignments": [
                    {
                        **_assignment_payload(row),
                        "employee_id": row.employee_id,
                        "employee_code": row.employee.employee_id,
                        "employee_name": row.employee.user.get_full_name() or row.employee.user.phone,
                        "designation": row.employee.designation,
                    }
                    for row in rows
                ],
            })

        try:
            employee = request.user.employee_profile
        except (AttributeError, EmployeeProfile.DoesNotExist):
            return Response({"detail": "Employee profile not found."}, status=404)

        rows = sync_training_assignments(employee)
        return Response({
            "scope": "EMPLOYEE",
            "assignments": [_assignment_payload(row) for row in rows],
        })


class TrainingDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "training"

    def get(self, request, assignment_id):
        role = str(getattr(request.user, "role", "")).upper()
        rows = EmployeeTrainingAssignment.objects.select_related("employee__user", "course", "penalty").prefetch_related("course__lessons", "trainer_reviews__trainer", "trainer_reviews__lesson")
        row = rows.filter(pk=assignment_id).first()
        if row is None:
            return Response({"detail": "Training assignment not found."}, status=404)
        if role == "ADMIN":
            company = request_company(request)
            if (company is not None and row.employee.company_id != company.id) or (
                company is None and row.employee.company_id is not None
            ):
                return Response({"detail": "Training assignment not found in this workspace."}, status=404)
        if role != "ADMIN" and row.employee.user_id != request.user.id:
            return Response({"detail": "You can only view your own training."}, status=403)
        enforce_assignment(row)
        return Response(_assignment_payload(row, include_content=True))


class TrainingLessonCompleteAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "training"

    def post(self, request, assignment_id, lesson_id):
        row = EmployeeTrainingAssignment.objects.select_related("course", "employee__user").filter(
            pk=assignment_id,
            employee__user=request.user,
        ).first()
        if row is None:
            return Response({"detail": "Training assignment not found."}, status=404)
        if row.status == "COMPLETED":
            return Response(_assignment_payload(row))

        lesson = row.course.lessons.filter(pk=lesson_id).first()
        if lesson is None:
            return Response({"detail": "Lesson not found in this course."}, status=404)
        if (lesson.video_asset or lesson.video_url) and request.data.get("video_watched") is not True:
            return Response(
                {"detail": "Please watch the complete Hindi training video before marking this lesson complete."},
                status=400,
            )

        completed = {int(v) for v in (row.lessons_completed or [])}
        completed.add(lesson.id)
        row.lessons_completed = sorted(completed)
        if row.status == "PENDING":
            row.status = "IN_PROGRESS"
        row.save(update_fields=["lessons_completed", "status"])
        return Response(_assignment_payload(row))


class TrainingQuizSubmitAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "training"

    @transaction.atomic
    def post(self, request, assignment_id):
        row = EmployeeTrainingAssignment.objects.select_for_update().select_related(
            "course", "employee__user"
        ).filter(pk=assignment_id, employee__user=request.user).first()
        if row is None:
            return Response({"detail": "Training assignment not found."}, status=404)
        if row.status == "COMPLETED":
            return Response(_assignment_payload(row))

        lessons = list(row.course.lessons.all())
        completed = {int(v) for v in (row.lessons_completed or [])}
        if lessons and len(completed) < len(lessons):
            return Response(
                {"detail": "Complete every lesson before taking the final quiz."},
                status=400,
            )

        questions = list(row.course.questions.all())
        if not questions:
            return Response({"detail": "This course has no quiz questions."}, status=400)
        raw_answers = request.data.get("answers") or {}
        answers = {str(k): str(v).upper().strip() for k, v in raw_answers.items()}

        correct = 0
        review = []
        for question in questions:
            selected = answers.get(str(question.id), "")
            is_correct = selected == question.correct_option
            if is_correct:
                correct += 1
            review.append({
                "question_id": question.id,
                "correct": is_correct,
                "selected": selected,
                "correct_option": question.correct_option,
                "explanation": question.explanation,
            })

        score = round(correct / len(questions) * 100)
        row.attempts += 1
        row.quiz_score = score
        passed = score >= row.course.passing_score
        if passed:
            row.status = "COMPLETED"
            row.completed_at = timezone.now()
            # Preserve the historical strike if training was completed late;
            # it remains visible to Admin for compliance history.
            _notify(
                request.user,
                f"training-complete:{row.id}",
                "Mandatory training completed",
                f"You passed {row.course.title} with {score}%.",
                priority="NORMAL",
                metadata={"assignment_id": row.id, "score": score},
            )
        elif row.status == "PENDING":
            row.status = "IN_PROGRESS"
        row.save(update_fields=["attempts", "quiz_score", "status", "completed_at"])

        return Response({
            "passed": passed,
            "score": score,
            "passing_score": row.course.passing_score,
            "attempts": row.attempts,
            "review": review,
            "assignment": _assignment_payload(row),
        })


def _admin_assignment_in_workspace(request, assignment):
    company = request_company(request)
    if company is not None:
        return assignment.employee.company_id == company.id
    return assignment.employee.company_id is None


class TrainingTrainerReviewAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "training"

    def post(self, request, assignment_id, lesson_id):
        if str(getattr(request.user, "role", "")).upper() != "ADMIN":
            return Response({"detail": "Only Admin/Trainer can submit coaching reviews."}, status=403)

        row = EmployeeTrainingAssignment.objects.select_related(
            "employee__user", "course"
        ).filter(pk=assignment_id).first()
        if row is None:
            return Response({"detail": "Training assignment not found."}, status=404)
        if not _admin_assignment_in_workspace(request, row):
            return Response({"detail": "Training assignment not found in this workspace."}, status=404)

        lesson = row.course.lessons.filter(pk=lesson_id).first()
        if lesson is None:
            return Response({"detail": "Lesson not found in this training plan."}, status=404)

        def score(name):
            try:
                value = int(request.data.get(name, 3))
            except (TypeError, ValueError):
                value = 3
            return max(1, min(5, value))

        review, _ = TrainingTrainerReview.objects.update_or_create(
            assignment=row,
            lesson=lesson,
            defaults={
                "trainer": request.user,
                "behaviour_score": score("behaviour_score"),
                "communication_score": score("communication_score"),
                "knowledge_score": score("knowledge_score"),
                "strengths": str(request.data.get("strengths", "")).strip(),
                "gaps": str(request.data.get("gaps", "")).strip(),
                "coaching_action": str(request.data.get("coaching_action", "")).strip(),
                "notes": str(request.data.get("notes", "")).strip(),
            },
        )

        _notify(
            row.employee.user,
            f"training-coaching:{row.id}:{lesson.id}",
            f"Training Day {lesson.day_number} coaching updated",
            (
                f"Trainer feedback saved. Behaviour {review.behaviour_score}/5, "
                f"Communication {review.communication_score}/5, Knowledge {review.knowledge_score}/5. "
                f"Improvement action: {review.coaching_action or 'Review trainer notes.'}"
            ),
            priority="NORMAL",
            metadata={"assignment_id": row.id, "lesson_id": lesson.id},
        )

        return Response({
            "message": "Trainer review saved.",
            "assignment_id": row.id,
            "lesson_id": lesson.id,
            "day_number": lesson.day_number,
            "behaviour_score": review.behaviour_score,
            "communication_score": review.communication_score,
            "knowledge_score": review.knowledge_score,
            "strengths": review.strengths,
            "gaps": review.gaps,
            "coaching_action": review.coaching_action,
            "notes": review.notes,
        })


class TrainingCertificateIssueAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "training"

    @transaction.atomic
    def post(self, request, assignment_id):
        if str(getattr(request.user, "role", "")).upper() != "ADMIN":
            return Response({"detail": "Only Admin can issue training certificates."}, status=403)

        row = EmployeeTrainingAssignment.objects.select_for_update().select_related(
            "employee__user", "course"
        ).filter(pk=assignment_id).first()
        if row is None:
            return Response({"detail": "Training assignment not found."}, status=404)
        if not _admin_assignment_in_workspace(request, row):
            return Response({"detail": "Training assignment not found in this workspace."}, status=404)
        if not row.course.certificate_enabled:
            return Response({"detail": "Certificate is disabled for this course."}, status=400)

        current = _certificate_payload(row)
        if not current["eligible"]:
            return Response(
                {
                    "detail": "Certification requirements are not complete.",
                    "certification": current,
                },
                status=400,
            )

        certificate = getattr(row, "certificate", None)
        if certificate is None:
            year = timezone.localdate().year
            while True:
                verification_code = secrets.token_urlsafe(18).replace("-", "").replace("_", "")[:24].upper()
                if not TrainingCertificate.objects.filter(verification_code=verification_code).exists():
                    break
            sequence = TrainingCertificate.objects.filter(
                certificate_number__startswith=f"ARI-CERT-{year}-"
            ).count() + 1
            certificate_number = f"ARI-CERT-{year}-{sequence:06d}"
            trainer_average = _trainer_average(row)
            if int(row.course.required_trainer_reviews or 0) == 0:
                final_score = Decimal(row.quiz_score).quantize(Decimal("0.01"))
            else:
                final_score = (
                    Decimal(row.quiz_score) * Decimal("0.60")
                    + (trainer_average * Decimal("20")) * Decimal("0.40")
                ).quantize(Decimal("0.01"))
            certificate = TrainingCertificate.objects.create(
                assignment=row,
                certificate_number=certificate_number,
                verification_code=verification_code,
                quiz_score=row.quiz_score,
                trainer_average=trainer_average.quantize(Decimal("0.01")),
                final_score=final_score,
                issued_by=request.user,
                valid_until=timezone.localdate() + timedelta(days=row.course.certificate_valid_days),
            )
            _notify(
                row.employee.user,
                f"training-certificate:{row.id}",
                "ARI Professional Certification issued",
                f"Certificate {certificate.certificate_number} has been issued and is valid until {certificate.valid_until:%d %b %Y}.",
                priority="HIGH",
                metadata={
                    "assignment_id": row.id,
                    "certificate_number": certificate.certificate_number,
                },
            )

        return Response(_certificate_payload(row), status=200)


class TrainingCertificateRevokeAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "training"

    def post(self, request, assignment_id):
        if str(getattr(request.user, "role", "")).upper() != "ADMIN":
            return Response({"detail": "Only Admin can revoke certificates."}, status=403)
        certificate = TrainingCertificate.objects.select_related(
            "assignment__employee__user", "assignment__course"
        ).filter(assignment_id=assignment_id).first()
        if certificate is None:
            return Response({"detail": "Certificate not found."}, status=404)
        if not _admin_assignment_in_workspace(request, certificate.assignment):
            return Response({"detail": "Certificate not found in this workspace."}, status=404)
        if certificate.revoked_at is None:
            certificate.revoked_at = timezone.now()
            certificate.revoked_by = request.user
            certificate.revoke_reason = str(request.data.get("reason", "")).strip()[:500]
            certificate.save(update_fields=["revoked_at", "revoked_by", "revoke_reason"])
        return Response(_certificate_payload(certificate.assignment))



def _admin_training_company(request):
    company = request_company(request)
    return company


def _unique_course_slug(title, company):
    base = slugify(title)[:140] or "training-course"
    prefix = company.slug if company is not None else "legacy"
    candidate = f"{prefix}-{base}"[:180]
    suffix = 2
    while TrainingCourse.objects.filter(slug=candidate).exists():
        tail = f"-{suffix}"
        candidate = f"{prefix}-{base}"[:180-len(tail)] + tail
        suffix += 1
    return candidate


def _admin_course_queryset(request):
    company = _admin_training_company(request)
    rows = TrainingCourse.objects.prefetch_related("lessons", "questions").order_by("-created_at")
    return rows.filter(company=company) if company is not None else rows.filter(company__isnull=True)


def _admin_course_payload(course, include_content=True):
    payload = {
        "id": course.id,
        "title": course.title,
        "slug": course.slug,
        "description": course.description,
        "audience": course.audience,
        "is_mandatory": course.is_mandatory,
        "passing_score": course.passing_score,
        "due_days": course.due_days,
        "grace_days": course.grace_days,
        "penalty_amount": str(course.penalty_amount),
        "is_active": course.is_active,
        "is_published": course.is_published,
        "certificate_enabled": course.certificate_enabled,
        "certificate_valid_days": course.certificate_valid_days,
        "required_trainer_reviews": course.required_trainer_reviews,
        "minimum_trainer_average": float(course.minimum_trainer_average),
        "lesson_count": course.lessons.count(),
        "question_count": course.questions.count(),
        "assignment_count": course.assignments.count(),
        "created_at": course.created_at.isoformat(),
    }
    if include_content:
        payload["lessons"] = [
            {
                "id": lesson.id,
                "order": lesson.order,
                "day_number": lesson.day_number,
                "title": lesson.title,
                "content": lesson.content,
                "key_takeaway": lesson.key_takeaway,
                "duration_minutes": lesson.duration_minutes,
                "trainer_script": lesson.trainer_script,
                "practice_task": lesson.practice_task,
                "video_asset": lesson.video_asset,
                "video_url": lesson.video_url,
                "resource_url": lesson.resource_url,
                "resource_label": lesson.resource_label,
            }
            for lesson in course.lessons.all()
        ]
        payload["questions"] = [
            {
                "id": q.id,
                "order": q.order,
                "question": q.question,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
                "correct_option": q.correct_option,
                "explanation": q.explanation,
            }
            for q in course.questions.all()
        ]
    return payload


class AdminTrainingCourseAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({
            "courses": [_admin_course_payload(course) for course in _admin_course_queryset(request)]
        })

    def post(self, request):
        company = _admin_training_company(request)
        title = str(request.data.get("title") or "").strip()
        description = str(request.data.get("description") or "").strip()
        audience = str(request.data.get("audience") or "ALL").upper()
        if not title:
            return Response({"detail": "Course title is required."}, status=400)
        if audience not in {x[0] for x in TrainingCourse.AUDIENCE_CHOICES}:
            return Response({"detail": "Select a valid course audience."}, status=400)
        try:
            passing_score = max(1, min(100, int(request.data.get("passing_score", 80))))
            due_days = max(1, int(request.data.get("due_days", 7)))
            grace_days = max(0, int(request.data.get("grace_days", 2)))
            required_reviews = max(0, int(request.data.get("required_trainer_reviews", 0)))
            certificate_valid_days = max(1, int(request.data.get("certificate_valid_days", 365)))
            minimum_trainer_average = Decimal(str(request.data.get("minimum_trainer_average", 3)))
            penalty_amount = max(Decimal("0"), Decimal(str(request.data.get("penalty_amount", 0) or 0)))
        except (TypeError, ValueError, ArithmeticError):
            return Response({"detail": "One or more numeric course settings are invalid."}, status=400)
        minimum_trainer_average = max(Decimal("1.00"), min(Decimal("5.00"), minimum_trainer_average))
        course = TrainingCourse.objects.create(
            company=company,
            title=title,
            slug=_unique_course_slug(title, company),
            description=description,
            audience=audience,
            is_mandatory=bool(request.data.get("is_mandatory", True)),
            passing_score=passing_score,
            due_days=due_days,
            grace_days=grace_days,
            penalty_amount=penalty_amount,
            certificate_enabled=bool(request.data.get("certificate_enabled", True)),
            certificate_valid_days=certificate_valid_days,
            required_trainer_reviews=required_reviews,
            minimum_trainer_average=minimum_trainer_average,
            is_active=True,
            is_published=False,
            created_by=request.user,
        )
        return Response(_admin_course_payload(course), status=201)


class AdminTrainingCourseDetailAPIView(APIView):
    permission_classes = [IsAdmin]

    def _course(self, request, course_id):
        return _admin_course_queryset(request).filter(pk=course_id).first()

    def get(self, request, course_id):
        course = self._course(request, course_id)
        if course is None:
            return Response({"detail": "Training course not found."}, status=404)
        return Response(_admin_course_payload(course))

    @transaction.atomic
    def patch(self, request, course_id):
        course = self._course(request, course_id)
        if course is None:
            return Response({"detail": "Training course not found."}, status=404)

        string_fields = {
            "title": 180,
            "description": None,
            "audience": 20,
        }
        for field, limit in string_fields.items():
            if field in request.data:
                value = str(request.data.get(field) or "").strip()
                if field == "title" and not value:
                    return Response({"detail": "Course title cannot be empty."}, status=400)
                if field == "audience" and value.upper() not in {x[0] for x in TrainingCourse.AUDIENCE_CHOICES}:
                    return Response({"detail": "Select a valid course audience."}, status=400)
                setattr(course, field, value.upper() if field == "audience" else (value[:limit] if limit else value))

        for field in ("is_mandatory", "certificate_enabled", "is_active"):
            if field in request.data:
                setattr(course, field, bool(request.data.get(field)))

        int_rules = {
            "passing_score": (1, 100),
            "due_days": (1, 3650),
            "grace_days": (0, 3650),
            "certificate_valid_days": (1, 3650),
            "required_trainer_reviews": (0, 365),
        }
        for field, (minimum, maximum) in int_rules.items():
            if field in request.data:
                try:
                    value = int(request.data.get(field))
                except (TypeError, ValueError):
                    return Response({"detail": f"{field} must be a number."}, status=400)
                setattr(course, field, max(minimum, min(maximum, value)))

        if "penalty_amount" in request.data:
            try:
                course.penalty_amount = max(Decimal("0"), Decimal(str(request.data.get("penalty_amount") or 0)))
            except ArithmeticError:
                return Response({"detail": "penalty_amount is invalid."}, status=400)
        if "minimum_trainer_average" in request.data:
            try:
                value = Decimal(str(request.data.get("minimum_trainer_average")))
            except ArithmeticError:
                return Response({"detail": "minimum_trainer_average is invalid."}, status=400)
            course.minimum_trainer_average = max(Decimal("1.00"), min(Decimal("5.00"), value))

        publish_requested = request.data.get("is_published")
        if publish_requested is True:
            if not course.lessons.exists():
                return Response({"detail": "Add at least one lesson before publishing."}, status=400)
            if not course.questions.exists():
                return Response({"detail": "Add at least one test question before publishing."}, status=400)
            course.is_published = True
        elif publish_requested is False:
            course.is_published = False

        course.save()
        if course.is_published and course.is_mandatory:
            employees = EmployeeProfile.objects.filter(is_active=True)
            if course.company_id:
                employees = employees.filter(company_id=course.company_id)
            else:
                employees = employees.filter(company__isnull=True)
            for employee in employees:
                if _eligible(course, employee):
                    sync_training_assignments(employee)
        return Response(_admin_course_payload(course))

    def delete(self, request, course_id):
        course = self._course(request, course_id)
        if course is None:
            return Response({"detail": "Training course not found."}, status=404)
        if course.assignments.exists():
            course.is_active = False
            course.is_published = False
            course.save(update_fields=["is_active", "is_published"])
            return Response({"message": "Course archived because training history exists."})
        course.delete()
        return Response(status=204)


class AdminTrainingLessonAPIView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, course_id):
        course = _admin_course_queryset(request).filter(pk=course_id).first()
        if course is None:
            return Response({"detail": "Training course not found."}, status=404)
        title = str(request.data.get("title") or "").strip()
        content = str(request.data.get("content") or "").strip()
        if not title or len(content) < 80:
            return Response({
                "detail": "Lesson title and meaningful training content (at least 80 characters) are required."
            }, status=400)
        try:
            order = int(request.data.get("order") or (course.lessons.count() + 1))
            day_number = int(request.data.get("day_number") or order)
            duration = max(5, int(request.data.get("duration_minutes") or 30))
        except (TypeError, ValueError):
            return Response({"detail": "Lesson order/day/duration is invalid."}, status=400)
        if course.lessons.filter(order=order).exists():
            return Response({"detail": "A lesson with this order already exists."}, status=409)
        lesson = TrainingLesson.objects.create(
            course=course,
            order=order,
            day_number=max(1, day_number),
            duration_minutes=min(480, duration),
            title=title[:180],
            content=content,
            key_takeaway=str(request.data.get("key_takeaway") or "").strip()[:300],
            trainer_script=str(request.data.get("trainer_script") or "").strip(),
            practice_task=str(request.data.get("practice_task") or "").strip(),
            video_url=str(request.data.get("video_url") or "").strip(),
            resource_url=str(request.data.get("resource_url") or "").strip(),
            resource_label=str(request.data.get("resource_label") or "").strip()[:120],
        )
        return Response(_admin_course_payload(course), status=201)


class AdminTrainingLessonDetailAPIView(APIView):
    permission_classes = [IsAdmin]

    def _objects(self, request, course_id, lesson_id):
        course = _admin_course_queryset(request).filter(pk=course_id).first()
        if course is None:
            return None, None
        return course, course.lessons.filter(pk=lesson_id).first()

    def patch(self, request, course_id, lesson_id):
        course, lesson = self._objects(request, course_id, lesson_id)
        if lesson is None:
            return Response({"detail": "Training lesson not found."}, status=404)
        for field in ("title", "content", "key_takeaway", "trainer_script", "practice_task", "video_url", "resource_url", "resource_label"):
            if field in request.data:
                value = str(request.data.get(field) or "").strip()
                if field == "content" and len(value) < 80:
                    return Response({"detail": "Lesson content must be at least 80 characters."}, status=400)
                setattr(lesson, field, value)
        for field in ("day_number", "duration_minutes"):
            if field in request.data:
                try:
                    setattr(lesson, field, max(1, int(request.data.get(field))))
                except (TypeError, ValueError):
                    return Response({"detail": f"{field} is invalid."}, status=400)
        lesson.save()
        return Response(_admin_course_payload(course))

    def delete(self, request, course_id, lesson_id):
        course, lesson = self._objects(request, course_id, lesson_id)
        if lesson is None:
            return Response({"detail": "Training lesson not found."}, status=404)
        if course.assignments.exists():
            return Response({"detail": "Cannot delete lessons after the course has been assigned. Archive the course and create a new version."}, status=409)
        lesson.delete()
        return Response(status=204)


class AdminTrainingQuestionAPIView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, course_id):
        course = _admin_course_queryset(request).filter(pk=course_id).first()
        if course is None:
            return Response({"detail": "Training course not found."}, status=404)
        question = str(request.data.get("question") or "").strip()
        options = [str(request.data.get(f"option_{x}") or "").strip() for x in "abcd"]
        correct = str(request.data.get("correct_option") or "").upper().strip()
        if not question or any(not x for x in options) or correct not in {"A", "B", "C", "D"}:
            return Response({"detail": "Question, all four options and correct answer are required."}, status=400)
        order = course.questions.count() + 1
        try:
            order = int(request.data.get("order") or order)
        except (TypeError, ValueError):
            return Response({"detail": "Question order is invalid."}, status=400)
        q = TrainingQuestion.objects.create(
            course=course,
            order=order,
            question=question[:500],
            option_a=options[0][:300],
            option_b=options[1][:300],
            option_c=options[2][:300],
            option_d=options[3][:300],
            correct_option=correct,
            explanation=str(request.data.get("explanation") or "").strip()[:500],
        )
        return Response(_admin_course_payload(course), status=201)


class AdminTrainingQuestionDetailAPIView(APIView):
    permission_classes = [IsAdmin]

    def _objects(self, request, course_id, question_id):
        course = _admin_course_queryset(request).filter(pk=course_id).first()
        if course is None:
            return None, None
        return course, course.questions.filter(pk=question_id).first()

    def patch(self, request, course_id, question_id):
        course, q = self._objects(request, course_id, question_id)
        if q is None:
            return Response({"detail": "Training question not found."}, status=404)
        for field in ("question", "option_a", "option_b", "option_c", "option_d", "explanation"):
            if field in request.data:
                setattr(q, field, str(request.data.get(field) or "").strip())
        if "correct_option" in request.data:
            correct = str(request.data.get("correct_option") or "").upper().strip()
            if correct not in {"A", "B", "C", "D"}:
                return Response({"detail": "Correct option must be A, B, C or D."}, status=400)
            q.correct_option = correct
        q.save()
        return Response(_admin_course_payload(course))

    def delete(self, request, course_id, question_id):
        course, q = self._objects(request, course_id, question_id)
        if q is None:
            return Response({"detail": "Training question not found."}, status=404)
        if course.assignments.exists():
            return Response({"detail": "Cannot delete test questions after assignment. Archive and version the course instead."}, status=409)
        q.delete()
        return Response(status=204)


class AdminTrainingAssignAPIView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, course_id):
        course = _admin_course_queryset(request).filter(pk=course_id, is_active=True, is_published=True).first()
        if course is None:
            return Response({"detail": "Publish the training course before assigning it."}, status=404)
        company = _admin_training_company(request)
        employees = EmployeeProfile.objects.filter(is_active=True)
        employees = employees.filter(company=company) if company is not None else employees.filter(company__isnull=True)

        ids = request.data.get("employee_ids")
        if isinstance(ids, list) and ids:
            employees = employees.filter(pk__in=ids)
        elif course.audience != "ALL":
            employees = employees.filter(designation=course.audience)

        today = timezone.localdate()
        created = 0
        existing = 0
        for employee in employees:
            if not _eligible(course, employee):
                continue
            _, was_created = EmployeeTrainingAssignment.objects.get_or_create(
                employee=employee,
                course=course,
                defaults={
                    "due_date": today + timedelta(days=course.due_days),
                    "grace_until": today + timedelta(days=course.due_days + course.grace_days),
                },
            )
            if was_created:
                created += 1
                _notify(
                    employee.user,
                    f"training-assigned:{course.id}:{employee.id}",
                    "New training assigned",
                    f"{course.title} has been assigned. Complete it by {today + timedelta(days=course.due_days):%d %b %Y}.",
                    priority="HIGH",
                    metadata={"course_id": course.id},
                )
            else:
                existing += 1
        return Response({"created": created, "already_assigned": existing})


class TrainingCertificatePDFAPIView(APIView):
    permission_classes = []

    @staticmethod
    def _safe_text(value):
        text = str(value or "")
        return text.encode("ascii", "ignore").decode("ascii").strip()

    def get(self, request, code):
        certificate = TrainingCertificate.objects.select_related(
            "assignment__employee__user",
            "assignment__course",
            "issued_by",
        ).filter(verification_code=code).first()
        if certificate is None:
            return Response({"detail": "Certificate not found."}, status=404)

        row = certificate.assignment
        payload = _certificate_payload(row)["certificate"]
        employee_name = self._safe_text(
            row.employee.user.get_full_name() or row.employee.user.phone
        )
        employee_code = self._safe_text(row.employee.employee_id)
        course_title = self._safe_text(row.course.title.split("/")[0].strip())
        status_label = payload["status"]

        verify_url = request.build_absolute_uri(
            f"/api/employees/hrms/training/certificates/verify/{certificate.verification_code}/"
        )
        qr = qrcode.QRCode(version=3, box_size=6, border=2)
        qr.add_data(verify_url)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = BytesIO()
        qr_image.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)

        buffer = BytesIO()
        page_width, page_height = landscape(A4)
        pdf = canvas.Canvas(buffer, pagesize=(page_width, page_height))
        pdf.setTitle(f"ARI Training Certificate - {certificate.certificate_number}")
        pdf.setAuthor("ARI SMART RO")

        navy = colors.HexColor("#0B1F3A")
        gold = colors.HexColor("#C99A2E")
        soft = colors.HexColor("#F5F7FA")
        muted = colors.HexColor("#5A6573")
        green = colors.HexColor("#147D50")
        red = colors.HexColor("#B42318")

        pdf.setFillColor(soft)
        pdf.rect(0, 0, page_width, page_height, fill=1, stroke=0)

        pdf.setStrokeColor(navy)
        pdf.setLineWidth(5)
        pdf.rect(24, 24, page_width - 48, page_height - 48, fill=0, stroke=1)
        pdf.setStrokeColor(gold)
        pdf.setLineWidth(1.5)
        pdf.rect(34, 34, page_width - 68, page_height - 68, fill=0, stroke=1)

        pdf.setFillColor(navy)
        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawCentredString(page_width / 2, page_height - 78, "ARI SMART RO")

        pdf.setFillColor(gold)
        pdf.setFont("Helvetica-Bold", 30)
        pdf.drawCentredString(
            page_width / 2, page_height - 125, "CERTIFICATE OF PROFESSIONAL EXCELLENCE"
        )

        pdf.setFillColor(muted)
        pdf.setFont("Helvetica", 13)
        pdf.drawCentredString(
            page_width / 2,
            page_height - 158,
            "This certificate is proudly awarded to",
        )

        pdf.setFillColor(navy)
        pdf.setFont("Helvetica-Bold", 27)
        pdf.drawCentredString(page_width / 2, page_height - 205, employee_name or employee_code)

        pdf.setFillColor(muted)
        pdf.setFont("Helvetica", 12)
        pdf.drawCentredString(
            page_width / 2,
            page_height - 230,
            f"Employee ID: {employee_code}",
        )

        pdf.setFillColor(navy)
        pdf.setFont("Helvetica", 13)
        pdf.drawCentredString(
            page_width / 2,
            page_height - 275,
            "for successfully completing the ARI corporate training programme",
        )
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawCentredString(
            page_width / 2,
            page_height - 302,
            course_title or "30-Day Customer Service & Professional Excellence",
        )

        box_y = 130
        box_h = 105
        box_x = 90
        box_w = page_width - 300
        pdf.setFillColor(colors.white)
        pdf.setStrokeColor(colors.HexColor("#D0D5DD"))
        pdf.roundRect(box_x, box_y, box_w, box_h, 10, fill=1, stroke=1)

        pdf.setFillColor(navy)
        pdf.setFont("Helvetica-Bold", 11)
        labels = [
            ("Quiz Score", f"{certificate.quiz_score}%"),
            ("Trainer Avg.", f"{certificate.trainer_average}/5"),
            ("Final Score", f"{certificate.final_score}%"),
            ("Valid Until", certificate.valid_until.strftime("%d %b %Y")),
        ]
        col_w = box_w / len(labels)
        for index, (label, value) in enumerate(labels):
            x = box_x + col_w * index + col_w / 2
            pdf.setFillColor(muted)
            pdf.setFont("Helvetica", 9)
            pdf.drawCentredString(x, box_y + 66, label)
            pdf.setFillColor(navy)
            pdf.setFont("Helvetica-Bold", 13)
            pdf.drawCentredString(x, box_y + 42, value)

        qr_x = page_width - 185
        qr_y = 115
        pdf.drawImage(
            ImageReader(qr_buffer),
            qr_x,
            qr_y,
            width=105,
            height=105,
            preserveAspectRatio=True,
            mask="auto",
        )
        pdf.setFillColor(muted)
        pdf.setFont("Helvetica", 8)
        pdf.drawCentredString(qr_x + 52, qr_y - 12, "Scan to verify")

        pdf.setFillColor(navy)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(70, 88, f"Certificate No: {certificate.certificate_number}")
        pdf.setFont("Helvetica", 8)
        pdf.drawString(70, 72, f"Verification Code: {certificate.verification_code}")
        pdf.drawString(
            70,
            56,
            f"Issued: {timezone.localtime(certificate.issued_at).strftime('%d %b %Y')}",
        )

        status_color = green if status_label == "VALID" else red
        pdf.setFillColor(status_color)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawRightString(page_width - 70, 82, f"STATUS: {status_label}")
        if status_label == "REVOKED" and certificate.revoke_reason:
            reason = self._safe_text(certificate.revoke_reason)[:75]
            pdf.setFont("Helvetica", 7)
            pdf.drawRightString(page_width - 70, 66, f"Reason: {reason}")

        pdf.setFillColor(muted)
        pdf.setFont("Helvetica-Oblique", 7.5)
        pdf.drawCentredString(
            page_width / 2,
            38,
            "Digitally generated by ARI SMART RO. Verify authenticity using the QR code.",
        )

        pdf.showPage()
        pdf.save()
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = (
            f'inline; filename="ARI-Certificate-{certificate.certificate_number}.pdf"'
        )
        response["Cache-Control"] = "private, max-age=300"
        return response


class TrainingCertificateVerifyAPIView(APIView):
    permission_classes = []

    def get(self, request, code):
        certificate = TrainingCertificate.objects.select_related(
            "assignment__employee__user", "assignment__course"
        ).filter(verification_code=code).first()
        if certificate is None:
            return Response({"valid": False, "detail": "Certificate not found."}, status=404)
        payload = _certificate_payload(certificate.assignment)
        status_label = payload["certificate"]["status"]
        return Response({
            "valid": status_label == "VALID",
            "certificate": payload["certificate"],
        })
