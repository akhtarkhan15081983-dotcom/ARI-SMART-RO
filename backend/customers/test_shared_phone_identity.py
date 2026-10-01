from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from customers.identity import unique_unlinked_customer_for_phone
from customers.models import Customer


class SharedPhoneIdentityTests(TestCase):
    def _customer(self, phone, name):
        return Customer.objects.create(
            name=name,
            phone=phone,
            address="Test Address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI TEST",
        )

    def _user(self, phone):
        return User.objects.create_user(
            phone=phone,
            role="CUSTOMER",
            is_verified=True,
            is_active=True,
        )

    def test_unique_legacy_phone_can_be_resolved(self):
        user = self._user("9810000001")
        customer = self._customer(user.phone, "Unique Legacy Customer")

        resolved = unique_unlinked_customer_for_phone(user.phone)

        self.assertEqual(resolved.id, customer.id)

    def test_shared_legacy_phone_fails_closed(self):
        user = self._user("9810000002")
        first = self._customer(user.phone, "Shared Customer One")
        second = self._customer(user.phone, "Shared Customer Two")

        resolved = unique_unlinked_customer_for_phone(user.phone)

        self.assertIsNone(resolved)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertIsNone(first.user_id)
        self.assertIsNone(second.user_id)

    def test_profile_does_not_auto_link_shared_phone(self):
        user = self._user("9810000003")
        first = self._customer(user.phone, "Shared Profile One")
        second = self._customer(user.phone, "Shared Profile Two")
        client = APIClient()
        client.force_authenticate(user)

        response = client.get("/api/customers/profile/")

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.data["profile_exists"])
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertIsNone(first.user_id)
        self.assertIsNone(second.user_id)

    def test_customer_list_exposes_no_shared_phone_record(self):
        user = self._user("9810000004")
        self._customer(user.phone, "Shared List One")
        self._customer(user.phone, "Shared List Two")
        client = APIClient()
        client.force_authenticate(user)

        response = client.get("/api/customers/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.data), [])

    def test_profile_still_links_single_legacy_customer(self):
        user = self._user("9810000005")
        customer = self._customer(user.phone, "Single Legacy Profile")
        client = APIClient()
        client.force_authenticate(user)

        response = client.get("/api/customers/profile/")

        self.assertEqual(response.status_code, 200)
        customer.refresh_from_db()
        self.assertEqual(customer.user_id, user.id)
        self.assertEqual(response.data["profile"]["id"], customer.id)
