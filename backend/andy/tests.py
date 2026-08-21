from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from andy.app_control import AndyAppControl
from andy.models import AndyConversation, AndyMessage


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
