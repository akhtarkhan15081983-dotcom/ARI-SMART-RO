from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User, UserNotification

from .models import (
    EmployeePenalty,
    EmployeeProfile,
    EmployeeTrainingAssignment,
    TrainingCourse,
    TrainingLesson,
    TrainingQuestion,
    TrainingTrainerReview,
)
from .training import enforce_assignment


class EmployeeTrainingTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone="9777700001",
            password="Strong@Test1",
            first_name="Admin",
            role="ADMIN",
            is_verified=True,
        )
        self.employee_user = User.objects.create_user(
            phone="9777700002",
            password="Strong@Test1",
            first_name="Ravi",
            role="ENGINEER",
            is_verified=True,
        )
        self.employee = EmployeeProfile.objects.create(
            user=self.employee_user,
            gender="MALE",
            joining_date=timezone.localdate() - timedelta(days=30),
            designation="ENGINEER",
            salary=Decimal("20000.00"),
            is_active=True,
        )
        self.course = TrainingCourse.objects.create(
            title="Customer Respect Test",
            slug="customer-respect-test",
            description="Mandatory customer handling course.",
            audience="ALL",
            is_mandatory=True,
            passing_score=80,
            due_days=7,
            grace_days=2,
            penalty_amount=Decimal("100.00"),
            created_by=self.admin,
        )
        self.lesson1 = TrainingLesson.objects.create(
            course=self.course,
            order=1,
            day_number=1,
            title="Listen first",
            content="Listen without interrupting and acknowledge the concern.",
        )
        self.lesson2 = TrainingLesson.objects.create(
            course=self.course,
            order=2,
            day_number=2,
            title="Resolve professionally",
            content="Explain the next action clearly and keep promises.",
        )
        for index in range(1, 6):
            TrainingQuestion.objects.create(
                course=self.course,
                order=index,
                question=f"Question {index}",
                option_a="Correct",
                option_b="Wrong B",
                option_c="Wrong C",
                option_d="Wrong D",
                correct_option="A",
                explanation="A is the professional response.",
            )

    def test_employee_course_auto_assignment_is_locked_until_admin_schedules(self):
        self.client.force_authenticate(self.employee_user)
        response = self.client.get("/api/employees/hrms/training/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["scope"], "EMPLOYEE")
        self.assertEqual(len(response.data["assignments"]), 1)
        self.assertFalse(response.data["assignments"][0]["scheduled"])

        assignment_id = response.data["assignments"][0]["id"]
        lesson = self.client.post(
            f"/api/employees/hrms/training/{assignment_id}/lessons/{self.lesson1.id}/complete/",
            {},
            format="json",
        )
        self.assertEqual(lesson.status_code, 423)
        self.assertIn("Admin has not scheduled", lesson.data["detail"])

    def test_employee_can_complete_lessons_and_pass_quiz(self):
        self.client.force_authenticate(self.employee_user)
        listing = self.client.get("/api/employees/hrms/training/")
        assignment_id = listing.data["assignments"][0]["id"]
        assignment = EmployeeTrainingAssignment.objects.get(pk=assignment_id)
        assignment.scheduled_start_at = timezone.now() - timedelta(days=2)
        assignment.due_date = timezone.localdate() + timedelta(days=30)
        assignment.grace_until = timezone.localdate() + timedelta(days=32)
        assignment.save(update_fields=["scheduled_start_at", "due_date", "grace_until"])

        for lesson in (self.lesson1, self.lesson2):
            done = self.client.post(
                f"/api/employees/hrms/training/{assignment_id}/lessons/{lesson.id}/complete/",
                {},
                format="json",
            )
            self.assertEqual(done.status_code, 200)

        answers = {
            str(question.id): "A"
            for question in self.course.questions.all()
        }
        result = self.client.post(
            f"/api/employees/hrms/training/{assignment_id}/quiz/",
            {"answers": answers},
            format="json",
        )
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.data["passed"])
        self.assertEqual(result.data["score"], 100)

        assignment = EmployeeTrainingAssignment.objects.get(pk=assignment_id)
        self.assertEqual(assignment.status, "COMPLETED")
        self.assertIsNotNone(assignment.completed_at)
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.employee_user,
                event_key=f"training-complete:{assignment_id}",
            ).exists()
        )


    def test_admin_schedules_training_and_only_one_day_opens(self):
        assignment = EmployeeTrainingAssignment.objects.create(
            employee=self.employee,
            course=self.course,
            due_date=timezone.localdate() + timedelta(days=7),
            grace_until=timezone.localdate() + timedelta(days=9),
        )
        self.client.force_authenticate(self.admin)
        start_at = timezone.now()
        scheduled = self.client.post(
            f"/api/employees/hrms/training/{assignment.id}/schedule/",
            {"start_at": start_at.isoformat()},
            format="json",
        )
        self.assertEqual(scheduled.status_code, 200)

        assignment.refresh_from_db()
        self.assertIsNotNone(assignment.scheduled_start_at)
        self.assertEqual(assignment.release_interval_days, 1)
        self.assertEqual(assignment.scheduled_by, self.admin)

        self.client.force_authenticate(self.employee_user)
        day1 = self.client.post(
            f"/api/employees/hrms/training/{assignment.id}/lessons/{self.lesson1.id}/complete/",
            {},
            format="json",
        )
        self.assertEqual(day1.status_code, 200)

        day2 = self.client.post(
            f"/api/employees/hrms/training/{assignment.id}/lessons/{self.lesson2.id}/complete/",
            {},
            format="json",
        )
        self.assertEqual(day2.status_code, 423)
        self.assertIn("opens on", day2.data["detail"])

        detail = self.client.get(
            f"/api/employees/hrms/training/{assignment.id}/"
        )
        lessons = detail.data["lessons"]
        self.assertFalse(lessons[0]["locked"])
        self.assertTrue(lessons[1]["locked"])
        self.assertEqual(lessons[1]["content"], "")

    def test_non_admin_cannot_schedule_training(self):
        assignment = EmployeeTrainingAssignment.objects.create(
            employee=self.employee,
            course=self.course,
            due_date=timezone.localdate() + timedelta(days=7),
            grace_until=timezone.localdate() + timedelta(days=9),
        )
        self.client.force_authenticate(self.employee_user)
        response = self.client.post(
            f"/api/employees/hrms/training/{assignment.id}/schedule/",
            {"start_at": timezone.now().isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


    def test_admin_can_record_trainer_review_and_employee_cannot(self):
        assignment = EmployeeTrainingAssignment.objects.create(
            employee=self.employee,
            course=self.course,
            due_date=timezone.localdate() + timedelta(days=30),
            grace_until=timezone.localdate() + timedelta(days=32),
        )
        self.client.force_authenticate(self.admin)
        url = (
            f"/api/employees/hrms/training/{assignment.id}/"
            f"lessons/{self.lesson1.id}/trainer-review/"
        )
        response = self.client.post(
            url,
            {
                "behaviour_score": 4,
                "communication_score": 3,
                "knowledge_score": 5,
                "strengths": "Calm listening",
                "gaps": "Needs clearer closing",
                "coaching_action": "Practice the closing script three times",
                "notes": "Day 1 role-play completed",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        review = TrainingTrainerReview.objects.get(
            assignment=assignment,
            lesson=self.lesson1,
        )
        self.assertEqual(review.trainer, self.admin)
        self.assertEqual(review.behaviour_score, 4)
        self.assertEqual(review.coaching_action, "Practice the closing script three times")

        self.client.force_authenticate(self.employee_user)
        denied = self.client.post(url, {"behaviour_score": 5}, format="json")
        self.assertEqual(denied.status_code, 403)

    def test_overdue_training_creates_one_draft_penalty_after_grace(self):
        assignment = EmployeeTrainingAssignment.objects.create(
            employee=self.employee,
            course=self.course,
            due_date=timezone.localdate() - timedelta(days=4),
            grace_until=timezone.localdate() - timedelta(days=2),
        )
        enforce_assignment(assignment)
        assignment.refresh_from_db()

        self.assertEqual(assignment.status, "OVERDUE")
        self.assertTrue(assignment.compliance_strike)
        self.assertTrue(assignment.penalty_created)
        self.assertIsNotNone(assignment.penalty_id)

        penalty = EmployeePenalty.objects.get(pk=assignment.penalty_id)
        self.assertEqual(penalty.status, "DRAFT")
        self.assertEqual(penalty.amount, Decimal("100.00"))

        enforce_assignment(assignment)
        self.assertEqual(
            EmployeePenalty.objects.filter(
                employee=self.employee,
                reason__contains="Mandatory training overdue after grace period",
            ).count(),
            1,
        )

    def test_admin_sees_training_compliance_summary(self):
        EmployeeTrainingAssignment.objects.create(
            employee=self.employee,
            course=self.course,
            scheduled_start_at=timezone.now(),
            due_date=timezone.localdate() + timedelta(days=1),
            grace_until=timezone.localdate() + timedelta(days=3),
        )
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/employees/hrms/training/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["scope"], "ADMIN")
        self.assertEqual(response.data["summary"]["total"], 1)
        self.assertEqual(response.data["summary"]["due_next_2_days"], 1)
