from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
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

    # An assignment exists for eligible employees, but compliance countdown
    # begins only when Admin schedules the training.
    if assignment.scheduled_start_at is None:
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


def _lesson_unlock_state(row, lesson, lessons, completed_ids, now=None):
    now = now or timezone.now()
    if lesson.id in completed_ids:
        return {
            "locked": False,
            "unlock_at": None,
            "lock_reason": "",
        }

    if row.scheduled_start_at is None:
        return {
            "locked": True,
            "unlock_at": None,
            "lock_reason": "Admin has not scheduled this training yet.",
        }

    unlock_at = row.scheduled_start_at + timedelta(
        days=max(0, int(lesson.day_number or 1) - 1) * max(1, int(row.release_interval_days or 1))
    )
    if now < unlock_at:
        return {
            "locked": True,
            "unlock_at": unlock_at.isoformat(),
            "lock_reason": f"Day {lesson.day_number} opens on {timezone.localtime(unlock_at):%d %b %Y}.",
        }

    previous = None
    for candidate in lessons:
        if candidate.order < lesson.order:
            previous = candidate
        else:
            break
    if previous is not None and previous.id not in completed_ids:
        return {
            "locked": True,
            "unlock_at": unlock_at.isoformat(),
            "lock_reason": f"Complete Day {previous.day_number} first.",
        }

    return {
        "locked": False,
        "unlock_at": unlock_at.isoformat(),
        "lock_reason": "",
    }


def _assignment_payload(row, include_content=False, admin_view=False):
    course = row.course
    lessons = list(course.lessons.all())
    completed_ids = {int(v) for v in (row.lessons_completed or [])}
    now = timezone.now()
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
        "scheduled": row.scheduled_start_at is not None,
        "scheduled_start_at": row.scheduled_start_at.isoformat() if row.scheduled_start_at else None,
        "release_interval_days": row.release_interval_days,
        "scheduled_by": (
            row.scheduled_by.get_full_name() or row.scheduled_by.phone
            if row.scheduled_by_id else None
        ),
    }
    if include_content:
        lesson_rows = []
        for lesson in lessons:
            gate = _lesson_unlock_state(row, lesson, lessons, completed_ids, now=now)
            can_view_content = admin_view or not gate["locked"] or lesson.id in completed_ids
            review = next((
                review for review in row.trainer_reviews.all()
                if review.lesson_id == lesson.id
            ), None)
            lesson_rows.append({
                "id": lesson.id,
                "order": lesson.order,
                "title": lesson.title,
                "content": lesson.content if can_view_content else "",
                "key_takeaway": lesson.key_takeaway if can_view_content else "",
                "video_asset": lesson.video_asset if can_view_content else "",
                "day_number": lesson.day_number,
                "duration_minutes": lesson.duration_minutes,
                "trainer_script": lesson.trainer_script if admin_view else "",
                "practice_task": lesson.practice_task if can_view_content else "",
                "trainer_review": None if review is None else {
                    "behaviour_score": review.behaviour_score,
                    "communication_score": review.communication_score,
                    "knowledge_score": review.knowledge_score,
                    "strengths": review.strengths,
                    "gaps": review.gaps,
                    "coaching_action": review.coaching_action,
                    "notes": review.notes,
                    "trainer_name": review.trainer.get_full_name() or review.trainer.phone,
                    "reviewed_at": review.reviewed_at.isoformat(),
                },
                "completed": lesson.id in completed_ids,
                **gate,
            })
        payload["lessons"] = lesson_rows
        all_lessons_done = bool(lessons) and all(
            lesson.id in completed_ids for lesson in lessons
        )
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
        ] if (admin_view or all_lessons_done) else []
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
                    "scheduled": sum(1 for r in rows if r.scheduled_start_at is not None),
                    "not_scheduled": sum(
                        1 for r in rows
                        if r.status != "COMPLETED" and r.scheduled_start_at is None
                    ),
                    "due_next_2_days": sum(
                        1 for r in rows
                        if (
                            r.status != "COMPLETED"
                            and r.scheduled_start_at is not None
                            and 0 <= (r.due_date - today).days <= 2
                        )
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
        return Response(
            _assignment_payload(
                row,
                include_content=True,
                admin_view=role == "ADMIN",
            )
        )


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

        lessons = list(row.course.lessons.all())
        lesson = next((item for item in lessons if item.pk == lesson_id), None)
        if lesson is None:
            return Response({"detail": "Lesson not found in this course."}, status=404)

        completed = {int(v) for v in (row.lessons_completed or [])}
        gate = _lesson_unlock_state(row, lesson, lessons, completed)
        if gate["locked"]:
            return Response(
                {
                    "detail": gate["lock_reason"],
                    "unlock_at": gate["unlock_at"],
                },
                status=423,
            )

        if lesson.video_asset and request.data.get("video_watched") is not True:
            return Response(
                {"detail": "Please watch the complete Hindi training video before marking this lesson complete."},
                status=400,
            )

        completed.add(lesson.id)
        row.lessons_completed = sorted(completed)
        completed_at = dict(row.lesson_completed_at or {})
        completed_at[str(lesson.id)] = timezone.now().isoformat()
        row.lesson_completed_at = completed_at
        if row.status == "PENDING":
            row.status = "IN_PROGRESS"
        row.save(update_fields=["lessons_completed", "lesson_completed_at", "status"])
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

        if row.scheduled_start_at is None:
            return Response(
                {"detail": "Admin has not scheduled this training yet."},
                status=423,
            )

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


class TrainingScheduleAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "training"

    @transaction.atomic
    def post(self, request, assignment_id):
        if str(getattr(request.user, "role", "")).upper() != "ADMIN":
            return Response({"detail": "Only Admin can schedule employee training."}, status=403)

        row = EmployeeTrainingAssignment.objects.select_for_update().select_related(
            "employee__user", "course"
        ).filter(pk=assignment_id).first()
        if row is None:
            return Response({"detail": "Training assignment not found."}, status=404)
        if row.status == "COMPLETED":
            return Response({"detail": "Completed training cannot be rescheduled."}, status=400)

        raw_start = str(request.data.get("start_at") or "").strip()
        start_at = parse_datetime(raw_start) if raw_start else None
        if start_at is None and raw_start:
            start_date = parse_date(raw_start)
            if start_date is not None:
                start_at = timezone.make_aware(
                    datetime.combine(start_date, time.min)
                )
        if start_at is None:
            return Response({"detail": "Select a valid training start date/time."}, status=400)
        if timezone.is_naive(start_at):
            start_at = timezone.make_aware(start_at)

        interval_days = 1
        planned_days = max(
            list(row.course.lessons.values_list("day_number", flat=True)) or [1]
        )
        due_span = max(int(row.course.due_days or 1), planned_days * interval_days)
        start_local_date = timezone.localtime(start_at).date()

        row.scheduled_start_at = start_at
        row.release_interval_days = interval_days
        row.scheduled_by = request.user
        row.schedule_updated_at = timezone.now()
        row.due_date = start_local_date + timedelta(days=due_span)
        row.grace_until = row.due_date + timedelta(days=row.course.grace_days)
        row.save(update_fields=[
            "scheduled_start_at",
            "release_interval_days",
            "scheduled_by",
            "schedule_updated_at",
            "due_date",
            "grace_until",
        ])

        _notify(
            row.employee.user,
            f"training-scheduled:{row.id}:{row.schedule_updated_at.date().isoformat()}",
            "Training schedule assigned",
            (
                f"{row.course.title} starts {timezone.localtime(start_at):%d %b %Y}. "
                "Only one training day opens at a time; the next day unlocks on its scheduled date."
            ),
            priority="HIGH",
            metadata={
                "assignment_id": row.id,
                "start_at": start_at.isoformat(),
                "release_interval_days": 1,
            },
        )
        return Response({
            "detail": "Training schedule saved.",
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
