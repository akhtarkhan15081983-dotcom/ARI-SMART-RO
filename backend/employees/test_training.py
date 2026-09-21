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
    TrainingCertificate,
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
            is_published=True,
            required_trainer_reviews=2,
            created_by=self.admin,
        )
        self.lesson1 = TrainingLesson.objects.create(
            course=self.course,
            order=1,
            title="Listen first",
            content="Listen without interrupting and acknowledge the concern.",
        )
        self.lesson2 = TrainingLesson.objects.create(
            course=self.course,
            order=2,
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

    def test_employee_course_auto_assignment_and_lesson_gate(self):
        self.client.force_authenticate(self.employee_user)
        response = self.client.get("/api/employees/hrms/training/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["scope"], "EMPLOYEE")
        self.assertEqual(len(response.data["assignments"]), 1)

        assignment_id = response.data["assignments"][0]["id"]
        quiz = self.client.post(
            f"/api/employees/hrms/training/{assignment_id}/quiz/",
            {"answers": {}},
            format="json",
        )
        self.assertEqual(quiz.status_code, 400)
        self.assertIn("Complete every lesson", quiz.data["detail"])

    def test_employee_can_complete_lessons_and_pass_quiz(self):
        self.client.force_authenticate(self.employee_user)
        listing = self.client.get("/api/employees/hrms/training/")
        assignment_id = listing.data["assignments"][0]["id"]

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

    def test_admin_can_issue_and_public_can_verify_certificate(self):
        assignment = EmployeeTrainingAssignment.objects.create(
            employee=self.employee,
            course=self.course,
            due_date=timezone.localdate() + timedelta(days=30),
            grace_until=timezone.localdate() + timedelta(days=32),
        )
        assignment.lessons_completed = [self.lesson1.id, self.lesson2.id]
        assignment.quiz_score = 100
        assignment.status = "COMPLETED"
        assignment.completed_at = timezone.now()
        assignment.save(
            update_fields=["lessons_completed", "quiz_score", "status", "completed_at"]
        )

        for lesson in (self.lesson1, self.lesson2):
            TrainingTrainerReview.objects.create(
                assignment=assignment,
                lesson=lesson,
                trainer=self.admin,
                behaviour_score=4,
                communication_score=4,
                knowledge_score=4,
                strengths="Professional",
                gaps="",
                coaching_action="Keep practicing",
            )

        self.client.force_authenticate(self.admin)
        issued = self.client.post(
            f"/api/employees/hrms/training/{assignment.id}/certificate/issue/",
            {},
            format="json",
        )
        self.assertEqual(issued.status_code, 200)
        self.assertTrue(issued.data["issued"])
        self.assertEqual(issued.data["certificate"]["status"], "VALID")

        certificate = TrainingCertificate.objects.get(assignment=assignment)
        self.assertEqual(certificate.quiz_score, 100)
        self.assertEqual(certificate.trainer_average, Decimal("4.00"))

        self.client.force_authenticate(user=None)
        verified = self.client.get(
            f"/api/employees/hrms/training/certificates/verify/{certificate.verification_code}/"
        )
        self.assertEqual(verified.status_code, 200)
        self.assertTrue(verified.data["valid"])
        self.assertEqual(
            verified.data["certificate"]["certificate_number"],
            certificate.certificate_number,
        )

    def test_public_certificate_pdf_is_generated(self):
        assignment = EmployeeTrainingAssignment.objects.create(
            employee=self.employee,
            course=self.course,
            due_date=timezone.localdate() + timedelta(days=30),
            grace_until=timezone.localdate() + timedelta(days=32),
            lessons_completed=[self.lesson1.id, self.lesson2.id],
            quiz_score=100,
            status="COMPLETED",
            completed_at=timezone.now(),
        )
        for lesson in (self.lesson1, self.lesson2):
            TrainingTrainerReview.objects.create(
                assignment=assignment,
                lesson=lesson,
                trainer=self.admin,
                behaviour_score=4,
                communication_score=4,
                knowledge_score=4,
            )
        self.client.force_authenticate(self.admin)
        self.client.post(
            f"/api/employees/hrms/training/{assignment.id}/certificate/issue/",
            {},
            format="json",
        )
        certificate = TrainingCertificate.objects.get(assignment=assignment)

        self.client.force_authenticate(user=None)
        response = self.client.get(
            f"/api/employees/hrms/training/certificates/{certificate.verification_code}/pdf/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_certificate_requires_all_trainer_reviews(self):
        assignment = EmployeeTrainingAssignment.objects.create(
            employee=self.employee,
            course=self.course,
            due_date=timezone.localdate() + timedelta(days=30),
            grace_until=timezone.localdate() + timedelta(days=32),
            lessons_completed=[self.lesson1.id, self.lesson2.id],
            quiz_score=100,
            status="COMPLETED",
            completed_at=timezone.now(),
        )
        TrainingTrainerReview.objects.create(
            assignment=assignment,
            lesson=self.lesson1,
            trainer=self.admin,
            behaviour_score=5,
            communication_score=5,
            knowledge_score=5,
        )
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f"/api/employees/hrms/training/{assignment.id}/certificate/issue/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["certification"]["requirements"]["trainer_reviews_complete"])
        self.assertFalse(TrainingCertificate.objects.filter(assignment=assignment).exists())

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
            due_date=timezone.localdate() + timedelta(days=1),
            grace_until=timezone.localdate() + timedelta(days=3),
        )
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/employees/hrms/training/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["scope"], "ADMIN")
        self.assertEqual(response.data["summary"]["total"], 1)
        self.assertEqual(response.data["summary"]["due_next_2_days"], 1)


class TrainingAcademyBuilderTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone="9777710001",
            password="Strong@Test1",
            first_name="Academy",
            role="ADMIN",
            is_verified=True,
        )
        self.employee_user = User.objects.create_user(
            phone="9777710002",
            password="Strong@Test1",
            first_name="Learner",
            role="ENGINEER",
            is_verified=True,
        )
        self.employee = EmployeeProfile.objects.create(
            user=self.employee_user,
            gender="MALE",
            joining_date=timezone.localdate(),
            designation="ENGINEER",
            salary=Decimal("21000.00"),
            is_active=True,
        )

    def test_admin_can_build_publish_assign_and_certify_test_based_course(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            "/api/employees/hrms/training/admin/courses/",
            {
                "title": "Pump & SV Diagnostic Academy",
                "description": "Detailed technical diagnostic and customer explanation course.",
                "audience": "ENGINEER",
                "passing_score": 80,
                "due_days": 10,
                "grace_days": 2,
                "certificate_enabled": True,
                "certificate_valid_days": 180,
                "required_trainer_reviews": 0,
                "minimum_trainer_average": 3,
                "is_mandatory": False,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        course_id = created.data["id"]
        self.assertFalse(created.data["is_published"])

        short_lesson = self.client.post(
            f"/api/employees/hrms/training/admin/courses/{course_id}/lessons/",
            {"title": "Too short", "content": "Short"},
            format="json",
        )
        self.assertEqual(short_lesson.status_code, 400)

        lesson = self.client.post(
            f"/api/employees/hrms/training/admin/courses/{course_id}/lessons/",
            {
                "title": "Diagnose before replacing",
                "content": (
                    "Start with the symptom, inspect power and water conditions, review job history, "
                    "check switches and valves, record evidence, isolate the likely fault, explain the "
                    "reasoning to the customer, and replace a part only when diagnosis supports it."
                ),
                "key_takeaway": "Evidence before replacement.",
                "practice_task": "Run a mock no-start diagnostic and explain the decision.",
                "trainer_script": "Demonstrate one wrong and one correct diagnostic sequence.",
                "duration_minutes": 60,
                "day_number": 1,
            },
            format="json",
        )
        self.assertEqual(lesson.status_code, 201)

        question = self.client.post(
            f"/api/employees/hrms/training/admin/courses/{course_id}/questions/",
            {
                "question": "What should happen before replacing the pump?",
                "option_a": "Replace it immediately",
                "option_b": "Evidence-based diagnosis",
                "option_c": "Ask the customer to choose",
                "option_d": "Close the job",
                "correct_option": "B",
                "explanation": "Diagnosis prevents unnecessary replacement.",
            },
            format="json",
        )
        self.assertEqual(question.status_code, 201)

        published = self.client.patch(
            f"/api/employees/hrms/training/admin/courses/{course_id}/",
            {"is_published": True},
            format="json",
        )
        self.assertEqual(published.status_code, 200)
        self.assertTrue(published.data["is_published"])

        assigned = self.client.post(
            f"/api/employees/hrms/training/admin/courses/{course_id}/assign/",
            {"employee_ids": [self.employee.id]},
            format="json",
        )
        self.assertEqual(assigned.status_code, 200)
        self.assertEqual(assigned.data["created"], 1)

        assignment = EmployeeTrainingAssignment.objects.get(
            employee=self.employee,
            course_id=course_id,
        )

        self.client.force_authenticate(self.employee_user)
        done = self.client.post(
            f"/api/employees/hrms/training/{assignment.id}/lessons/{assignment.course.lessons.first().id}/complete/",
            {},
            format="json",
        )
        self.assertEqual(done.status_code, 200)

        q = assignment.course.questions.first()
        result = self.client.post(
            f"/api/employees/hrms/training/{assignment.id}/quiz/",
            {"answers": {str(q.id): "B"}},
            format="json",
        )
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.data["passed"])

        self.client.force_authenticate(self.admin)
        certificate = self.client.post(
            f"/api/employees/hrms/training/{assignment.id}/certificate/issue/",
            {},
            format="json",
        )
        self.assertEqual(certificate.status_code, 200)
        self.assertTrue(certificate.data["issued"])
        self.assertEqual(certificate.data["certificate"]["final_score"], 100.0)

    def test_course_cannot_publish_without_lesson_and_question(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            "/api/employees/hrms/training/admin/courses/",
            {"title": "Incomplete Draft", "audience": "ALL"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        response = self.client.patch(
            f"/api/employees/hrms/training/admin/courses/{created.data['id']}/",
            {"is_published": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("lesson", response.data["detail"].lower())
