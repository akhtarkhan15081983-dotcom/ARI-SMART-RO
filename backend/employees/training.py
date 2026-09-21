from datetime import timedelta
from decimal import Decimal
import secrets

from django.db import transaction
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserNotification
from tenancy.access import HasRequiredFeature

from .models import (
    EmployeePenalty,
    EmployeeProfile,
    EmployeeTrainingAssignment,
    TrainingCourse,
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


def sync_training_assignments(employee):
    today = timezone.localdate()
    for course in TrainingCourse.objects.filter(is_active=True, is_mandatory=True):
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
    required_reviews = lesson_count
    trainer_reviews_complete = reviews_count >= required_reviews
    trainer_standard_met = trainer_reviews_complete and trainer_average >= Decimal("3.00")
    eligible = (
        row.status == "COMPLETED"
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
            "minimum_trainer_average": 3.0,
            "trainer_average": float(round(trainer_average, 2)),
        },
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
            for employee in EmployeeProfile.objects.filter(is_active=True):
                sync_training_assignments(employee)
            rows = EmployeeTrainingAssignment.objects.select_related(
                "employee__user", "course", "penalty"
            ).order_by("status", "due_date", "employee__employee_id")
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
        if lesson.video_asset and request.data.get("video_watched") is not True:
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
                valid_until=timezone.localdate() + timedelta(days=365),
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
        if certificate.revoked_at is None:
            certificate.revoked_at = timezone.now()
            certificate.revoked_by = request.user
            certificate.revoke_reason = str(request.data.get("reason", "")).strip()[:500]
            certificate.save(update_fields=["revoked_at", "revoked_by", "revoke_reason"])
        return Response(_certificate_payload(certificate.assignment))


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
