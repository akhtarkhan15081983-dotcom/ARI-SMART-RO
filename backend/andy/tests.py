from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from andy.action_control import AndyActionControl
from andy.app_control import AndyAppControl
from andy.models import AndyConversation, AndyKnowledge, AndyMessage, AndyPendingAction, AndySpeechJob, AndyTeaching
from andy.local_tts import LocalTTS
from assets.models import ROAsset
from customers.models import Customer
from employees.models import EmployeeProfile
from jobs.models import Job
from products.models import ProductCategory, ROModel


class AndyAppControlTests(TestCase):
    def setUp(self):
        self.engineer_user = User.objects.create_user(
            phone="9000000001",
            password="test-pass",
            first_name="Test",
            role="ENGINEER",
        )
        self.customer_user = User.objects.create_user(
            phone="9000000002",
            password="test-pass",
            first_name="Customer",
            role="CUSTOMER",
        )

    def test_capabilities_are_handled_without_llm(self):
        result = AndyAppControl(self.engineer_user).try_handle("Andy, tum kya kya kar sakte ho?")
        self.assertIsNotNone(result)
        self.assertTrue(result["handled"])
        self.assertEqual(result["intent"], "capabilities")
        self.assertIn("ARI SMART RO", result["answer"])

    def test_non_engineer_does_not_receive_engineer_job_tool(self):
        result = AndyAppControl(self.customer_user).try_handle("mere aaj ke jobs batao")
        self.assertIsNone(result)

    def test_unlinked_customer_gets_safe_linking_message(self):
        result = AndyAppControl(self.customer_user).try_handle("meri complaints batao")
        self.assertIsNotNone(result)
        self.assertEqual(result["intent"], "customer_profile_missing")
        self.assertIn("linked", result["answer"])

    def test_customer_cannot_get_global_operations_summary(self):
        result = AndyAppControl(self.customer_user).try_handle("operations summary batao")
        self.assertIsNone(result)

    def test_admin_can_get_operations_summary(self):
        admin = User.objects.create_user(
            phone="9000000003",
            password="test-pass",
            first_name="Admin",
            role="ADMIN",
        )
        result = AndyAppControl(admin).try_handle("operations summary batao")
        self.assertIsNotNone(result)
        self.assertEqual(result["intent"], "operations_summary")
        self.assertIn("pending jobs", result["answer"])
        self.assertIn("open complaints", result["answer"])


class AndyActionControlTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="9000000101",
            password="test-pass",
            first_name="Action",
            role="ENGINEER",
        )
        self.engineer = EmployeeProfile.objects.create(
            user=self.user,
            employee_id="EMP-TEST-001",
            gender="MALE",
            joining_date=timezone.localdate(),
            designation="ENGINEER",
        )
        self.other_user = User.objects.create_user(
            phone="9000000102",
            password="test-pass",
            first_name="Other",
            role="ENGINEER",
        )
        self.other_engineer = EmployeeProfile.objects.create(
            user=self.other_user,
            employee_id="EMP-TEST-002",
            gender="MALE",
            joining_date=timezone.localdate(),
            designation="ENGINEER",
        )
        self.customer = Customer.objects.create(
            name="Test Customer",
            phone="9000000201",
            address="Test Address",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            ro_model="Test RO",
        )
        category = ProductCategory.objects.create(name="Test Category")
        ro_model = ROModel.objects.create(
            category=category,
            model_name="Test Model",
            capacity="12 LPH",
            business_type="RENT",
        )
        self.asset = ROAsset.objects.create(
            ro_model=ro_model,
            serial_number="TEST-SERIAL-001",
        )
        self.job = Job.objects.create(
            customer=self.customer,
            ro_asset=self.asset,
            engineer=self.engineer,
            job_type="SERVICE",
            scheduled_date=timezone.now(),
            status="ASSIGNED",
        )

    def test_write_request_without_job_id_does_not_create_pending_action(self):
        result = AndyActionControl(self.user).propose("Andy accept job")
        self.assertEqual(result["intent"], "job_action_needs_id")
        self.assertFalse(result["requires_confirmation"])
        self.assertEqual(AndyPendingAction.objects.count(), 0)

    def test_engineer_cannot_propose_action_for_another_engineers_job(self):
        other_job = Job.objects.create(
            customer=self.customer,
            ro_asset=self.asset,
            engineer=self.other_engineer,
            job_type="SERVICE",
            scheduled_date=timezone.now(),
            status="ASSIGNED",
        )
        result = AndyActionControl(self.user).propose(f"accept job {other_job.job_id}")
        self.assertEqual(result["intent"], "job_action_not_allowed")
        self.assertEqual(AndyPendingAction.objects.count(), 0)

    def test_proposal_does_not_mutate_job_before_confirmation(self):
        result = AndyActionControl(self.user).propose(f"accept job {self.job.job_id}")
        self.assertTrue(result["requires_confirmation"])
        self.assertEqual(result["intent"], "job_status_confirmation")
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "ASSIGNED")
        action = AndyPendingAction.objects.get(id=result["pending_action_id"])
        self.assertEqual(action.status, "PENDING")
        self.assertEqual(action.payload["new_status"], "ACCEPTED")

    def test_cancel_keeps_job_unchanged(self):
        proposed = AndyActionControl(self.user).propose(f"accept job {self.job.job_id}")
        result = AndyActionControl(self.user).resolve(proposed["pending_action_id"], False)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "CANCELLED")
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "ASSIGNED")
        action = AndyPendingAction.objects.get(id=proposed["pending_action_id"])
        self.assertEqual(action.status, "CANCELLED")

    def test_confirm_executes_valid_domain_transition(self):
        proposed = AndyActionControl(self.user).propose(f"accept job {self.job.job_id}")
        result = AndyActionControl(self.user).resolve(proposed["pending_action_id"], True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "CONFIRMED")
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "ACCEPTED")
        self.assertIsNotNone(self.job.accepted_at)
        self.assertTrue(self.job.activity_logs.filter(activity="Job Accepted").exists())

    def test_same_pending_action_cannot_be_confirmed_twice(self):
        proposed = AndyActionControl(self.user).propose(f"accept job {self.job.job_id}")
        first = AndyActionControl(self.user).resolve(proposed["pending_action_id"], True)
        second = AndyActionControl(self.user).resolve(proposed["pending_action_id"], True)
        self.assertTrue(first["ok"])
        self.assertFalse(second["ok"])
        self.assertEqual(second["status_code"], 409)

    def test_other_user_cannot_resolve_pending_action(self):
        proposed = AndyActionControl(self.user).propose(f"accept job {self.job.job_id}")
        result = AndyActionControl(self.other_user).resolve(proposed["pending_action_id"], True)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status_code"], 404)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "ASSIGNED")


class AndyChatAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone="9000000011",
            password="test-pass",
            first_name="Engineer",
            role="ENGINEER",
        )

    def test_chat_requires_authentication(self):
        response = self.client.post("/api/andy/chat/", {"message": "hello"}, format="json")
        self.assertIn(response.status_code, (401, 403))

    def test_empty_message_is_rejected(self):
        self.client.force_authenticate(self.user)
        response = self.client.post("/api/andy/chat/", {"message": "   "}, format="json")
        self.assertEqual(response.status_code, 400)

    @patch("andy.views.LocalLLM.chat", side_effect=AssertionError("LLM must not run for deterministic app-control intent"))
    def test_capability_intent_uses_fast_app_control_path(self, _mock_chat):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/andy/chat/",
            {"message": "Andy, tum kya kya kar sakte ho?"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["source"], "app_control")
        self.assertEqual(data["intent"], "capabilities")
        self.assertIn("ARI SMART RO", data["answer"])

        conversation = AndyConversation.objects.get(id=data["conversation_id"])
        self.assertEqual(conversation.user, self.user)
        self.assertEqual(conversation.messages.filter(role="USER").count(), 1)
        self.assertEqual(conversation.messages.filter(role="ASSISTANT").count(), 1)

    @patch("andy.views.LocalLLM.chat", return_value="I am ANDY.")
    def test_llm_fallback_persists_only_to_authenticated_users_conversation(self, _mock_chat):
        self.client.force_authenticate(self.user)
        response = self.client.post("/api/andy/chat/", {"message": "Who are you?"}, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["source"], "local_llm")
        conversation = AndyConversation.objects.get(id=data["conversation_id"])
        self.assertEqual(conversation.user, self.user)

    def test_user_cannot_submit_feedback_for_another_users_message(self):
        other = User.objects.create_user(
            phone="9000000012",
            password="test-pass",
            first_name="Other",
            role="ENGINEER",
        )
        conversation = AndyConversation.objects.create(user=other, title="private")
        message = AndyMessage.objects.create(conversation=conversation, role="ASSISTANT", content="private answer")

        self.client.force_authenticate(self.user)
        response = self.client.post(
            f"/api/andy/feedback/{message.id}/",
            {"rating": 2},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_memory_is_scoped_to_authenticated_user(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/andy/memory/",
            {"key": "preferred_language", "value": "Hinglish"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.user.andy_memories.filter(key="preferred_language", value="Hinglish").exists())

    def test_action_confirmation_requires_boolean(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/andy/actions/999/confirm/",
            {"confirm": "yes"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class AndySpeakAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone="9000000031",
            password="test-pass",
            first_name="Voice",
            role="ENGINEER",
        )

    def test_speak_requires_authentication(self):
        response = self.client.post("/api/andy/speak/", {"text": "hello"}, format="json")
        self.assertIn(response.status_code, (401, 403))

    def test_speak_rejects_empty_text(self):
        self.client.force_authenticate(self.user)
        response = self.client.post("/api/andy/speak/", {"text": "   "}, format="json")
        self.assertEqual(response.status_code, 400)

    @patch("andy.views.enqueue_speech_job")
    def test_speak_queues_background_job(self, mock_enqueue):
        self.client.force_authenticate(self.user)
        response = self.client.post("/api/andy/speak/", {"text": "Namaste"}, format="json")
        self.assertEqual(response.status_code, 202)
        job = AndySpeechJob.objects.get(id=response.json()["job_id"])
        self.assertEqual(job.status, "PENDING")
        mock_enqueue.assert_called_once_with(job.id)

    def test_completed_speech_job_returns_wav(self):
        job = AndySpeechJob.objects.create(
            user=self.user, text="Namaste", status="COMPLETED", audio=b"RIFF" + b"0" * 64
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/andy/speak/{job.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "audio/wav")
        self.assertEqual(response["X-Andy-Avatar-State"], "SPEAKING")

    def test_pending_speech_job_reports_status(self):
        job = AndySpeechJob.objects.create(user=self.user, text="Namaste")
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/andy/speak/{job.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "PENDING")

    @patch("andy.views.enqueue_speech_job")
    def test_speak_reuses_existing_job_for_same_text(self, mock_enqueue):
        job = AndySpeechJob.objects.create(user=self.user, text="Namaste", status="COMPLETED", audio=b"RIFF")
        self.client.force_authenticate(self.user)
        response = self.client.post("/api/andy/speak/", {"text": "Namaste"}, format="json")
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["job_id"], str(job.id))
        mock_enqueue.assert_not_called()

    def test_failed_speech_job_reports_tts_error(self):
        job = AndySpeechJob.objects.create(user=self.user, text="Namaste", status="FAILED", error="voice failed")
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/andy/speak/{job.id}/")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["message"], "voice failed")

    def test_speech_job_is_private_to_owner(self):
        other = User.objects.create_user(phone="9000000032", password="test-pass", role="ENGINEER")
        job = AndySpeechJob.objects.create(user=other, text="private")
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/andy/speak/{job.id}/")
        self.assertEqual(response.status_code, 404)

    def test_default_indic_python_uses_repo_voice_v2_environment(self):
        tts = LocalTTS()
        self.assertEqual(tts.indic_python.name, "python.exe")
        self.assertEqual(tts.indic_python.parent.parent.name, "voice_v2_clean")

    @patch.dict("os.environ", {"ANDY_INDICF5_ALLOW_CPU": "0"})
    def test_auto_voice_avoids_slow_cpu_indicf5(self):
        self.assertFalse(LocalTTS()._indicf5_fast_enough_for_auto())


class AndyTeachingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="9000000301",
            password="test-pass",
            first_name="Teacher",
            role="CUSTOMER",
        )
        self.admin = User.objects.create_user(
            phone="9000000302",
            password="test-pass",
            first_name="Reviewer",
            role="ADMIN",
            is_superuser=True,
            is_staff=True,
        )
        self.client = APIClient()
        self.conversation = AndyConversation.objects.create(
            user=self.user,
            title="Teaching test",
        )
        AndyMessage.objects.create(
            conversation=self.conversation,
            role="USER",
            content="UV chamber quartz sleeve ko kab clean karein?",
        )
        self.assistant_message = AndyMessage.objects.create(
            conversation=self.conversation,
            role="ASSISTANT",
            content="Mujhe pakka nahi pata.",
        )

    def test_bad_feedback_with_correction_creates_pending_teaching(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            f"/api/andy/feedback/{self.assistant_message.id}/",
            {"rating": 1, "correction": "Quartz sleeve ko scale ke hisab se service par inspect aur clean karein."},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        teaching = AndyTeaching.objects.get(id=response.data["teaching_id"])
        self.assertEqual(teaching.status, "PENDING")
        self.assertEqual(teaching.submitted_by, self.user)
        self.assertIn("quartz sleeve", teaching.question.lower())

    def test_regular_user_cannot_review_teaching(self):
        teaching = AndyTeaching.objects.create(
            submitted_by=self.user,
            question="UV chamber quartz sleeve ko kab clean karein?",
            answer="Service par inspect karein.",
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(
            f"/api/andy/teach/{teaching.id}/review/",
            {"action": "APPROVE"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        teaching.refresh_from_db()
        self.assertEqual(teaching.status, "PENDING")

    def test_admin_approval_creates_retrievable_knowledge(self):
        teaching = AndyTeaching.objects.create(
            submitted_by=self.user,
            question="UV chamber quartz sleeve ko kab clean karein?",
            answer="Quartz sleeve ko scale ke hisab se service par inspect aur clean karein.",
        )
        self.client.force_authenticate(self.admin)
        review = self.client.post(
            f"/api/andy/teach/{teaching.id}/review/",
            {"action": "APPROVE"},
            format="json",
        )
        self.assertEqual(review.status_code, 200)
        teaching.refresh_from_db()
        self.assertEqual(teaching.status, "APPROVED")
        self.assertIsNotNone(teaching.knowledge_id)
        self.assertTrue(
            AndyKnowledge.objects.filter(
                id=teaching.knowledge_id,
                namespace="andy-approved",
                is_active=True,
            ).exists()
        )

        self.client.force_authenticate(self.user)
        with patch("andy.views.LocalLLM.chat") as llm_chat:
            response = self.client.post(
                "/api/andy/chat/",
                {"message": "UV chamber quartz sleeve ko kab clean karein?"},
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["source"], "approved_knowledge")
        self.assertIn("inspect aur clean", response.data["answer"])
        llm_chat.assert_not_called()

    def test_direct_teach_submission_is_pending(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/andy/teach/",
            {
                "question": "Pre-filter kab badalna chahiye?",
                "answer": "Flow aur filter condition inspect karke badlein.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "PENDING")
