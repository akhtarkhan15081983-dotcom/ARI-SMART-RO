from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from customers.models import Customer, CustomerRentHistory
from .models import CustomerEngagement, User


class CustomerEngagementAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="9000000101", password="Strong@Test1", role="CUSTOMER", first_name="Ari")
        self.other = User.objects.create_user(phone="9000000102", password="Strong@Test2", role="CUSTOMER", first_name="Other")
        self.customer = Customer.objects.create(
            user=self.user, name="Ari Customer", phone=self.user.phone, address="Test",
            city="Agra", state="UP", pincode="282001", ro_model="Rental RO",
        )
        self.client.force_authenticate(self.user)

    def test_only_global_and_own_targeted_offers_are_returned(self):
        CustomerEngagement.objects.create(title="Everyone", message="Global", audience="ALL")
        CustomerEngagement.objects.create(title="Mine", message="Targeted", audience="TARGETED", target_user=self.user)
        CustomerEngagement.objects.create(title="Other", message="Hidden", audience="TARGETED", target_user=self.other)
        response = self.client.get("/api/auth/customer-engagement/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({row["title"] for row in response.data["items"]}, {"Everyone", "Mine"})

    def test_rent_due_is_derived_from_customer_ledger(self):
        CustomerRentHistory.objects.create(
            customer=self.customer, rent_month=date.today().replace(day=1),
            expected_rent=Decimal("500"), paid_amount=Decimal("200"),
        )
        response = self.client.get("/api/auth/customer-engagement/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["payment_alert"]["amount_due"], "300")

    def test_expired_offer_is_hidden(self):
        CustomerEngagement.objects.create(
            title="Expired", message="Old", audience="ALL",
            valid_until=timezone.now() - timedelta(minutes=1),
        )
        response = self.client.get("/api/auth/customer-engagement/")
        self.assertEqual(response.data["items"], [])

    def test_guest_sees_public_but_not_targeted_offer(self):
        CustomerEngagement.objects.create(title="Public", message="Visible", audience="ALL")
        CustomerEngagement.objects.create(title="Private", message="Hidden", audience="TARGETED", target_user=self.user)
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/auth/customer-engagement/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["title"] for row in response.data["items"]], ["Public"])
        self.assertIsNone(response.data["payment_alert"])
