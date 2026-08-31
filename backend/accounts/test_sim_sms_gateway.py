import hashlib
import time
from uuid import uuid4

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from customers.models import Customer

from .models import SimVerificationChallenge, SmsGatewayDevice, SmsGatewaySubmission, User


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


@override_settings(DISABLE_AUTH_THROTTLING=True, ARI_SMS_GATEWAY_NUMBER="919999999999")
class SimSmsGatewayTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.key = "gateway-secret-for-tests"
        self.gateway = SmsGatewayDevice.objects.create(
            device_id="OFFICE-01",
            name="Office Gateway",
            secret_hash=digest(self.key),
            phone_number="9999999999",
        )
        self.user = User.objects.create_user(
            phone="9300000001",
            password="Strong@123",
            role="CUSTOMER",
            is_verified=False,
        )
        self.customer = Customer.objects.create(
            name="Existing Customer",
            phone=self.user.phone,
            address="Address",
            city="Bareilly",
            state="UP",
            pincode="243001",
            ro_model="ARI RO",
        )

    def _start(self):
        response = self.client.post(
            "/api/auth/sim-verification/start/",
            {"phone": self.user.phone, "new_password": "NewStrong@123"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return response.data

    def _ingest(self, sender, message, nonce=None):
        return self.client.post(
            "/api/auth/sms-gateway/ingest/",
            {"sender_phone": sender, "message": message},
            format="json",
            HTTP_X_ARI_GATEWAY_ID=self.gateway.device_id,
            HTTP_X_ARI_GATEWAY_KEY=self.key,
            HTTP_X_ARI_NONCE=nonce or uuid4().hex,
            HTTP_X_ARI_TIMESTAMP=str(int(time.time())),
        )

    def test_matching_sim_sms_verifies_and_links_existing_customer(self):
        started = self._start()
        response = self._ingest(self.user.phone, started["sms_body"])
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["accepted"])
        self.user.refresh_from_db()
        self.customer.refresh_from_db()
        self.assertTrue(self.user.is_verified)
        self.assertEqual(self.customer.user, self.user)

        poll = self.client.post(
            "/api/auth/sim-verification/poll/",
            {"challenge_id": started["challenge_id"], "poll_secret": started["poll_secret"]},
            format="json",
        )
        self.assertEqual(poll.data["status"], "VERIFIED")
        self.assertIn("access", poll.data)

    def test_sender_number_must_match_registered_phone(self):
        started = self._start()
        response = self._ingest("9300000099", started["sms_body"])
        self.assertFalse(response.data["accepted"])
        self.assertEqual(response.data["result_code"], "SENDER_MISMATCH")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)

    def test_gateway_key_and_nonce_replay_are_enforced(self):
        started = self._start()
        nonce = uuid4().hex
        first = self._ingest(self.user.phone, started["sms_body"], nonce)
        self.assertEqual(first.status_code, 200)
        replay = self._ingest(self.user.phone, started["sms_body"], nonce)
        self.assertEqual(replay.status_code, 409)
        self.assertEqual(SmsGatewaySubmission.objects.filter(nonce=nonce).count(), 1)

        denied = self.client.post(
            "/api/auth/sms-gateway/ingest/",
            {"sender_phone": self.user.phone, "message": "ARI VERIFY DEADBEEF"},
            format="json",
            HTTP_X_ARI_GATEWAY_ID=self.gateway.device_id,
            HTTP_X_ARI_GATEWAY_KEY="wrong",
            HTTP_X_ARI_NONCE=uuid4().hex,
            HTTP_X_ARI_TIMESTAMP=str(int(time.time())),
        )
        self.assertEqual(denied.status_code, 401)
