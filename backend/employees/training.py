from datetime import timedelta
from decimal import Decimal

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
    }
    if include_content:
        payload["lessons"] = [
            {
                "id": lesson.id,
                "order": lesson.order,
                "title": lesson.title,
                "content": lesson.content,
                "key_takeaway": lesson.key_takeaway,
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
        rows = EmployeeTrainingAssignment.objects.select_related("employee__user", "course", "penalty")
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
