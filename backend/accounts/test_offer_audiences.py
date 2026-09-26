from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from customers.models import Customer
from .models import CustomerEngagement, User, UserNotification


class OfferAudienceTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone="9777700001",
            password="Strong@Test1",
            role="ADMIN",
            is_verified=True,
        )
        self.active_user = User.objects.create_user(
            phone="9777700002",
            password="Strong@Test1",
            role="CUSTOMER",
            is_verified=True,
        )
        self.inactive_user = User.objects.create_user(
            phone="9777700003",
            password="Strong@Test1",
            role="CUSTOMER",
            is_verified=True,
        )
        self.active_customer = Customer.objects.create(
            user=self.active_user,
            name="Active Customer",
            phone=self.active_user.phone,
            address="A",
            city="Mathura",
            state="Uttar Pradesh",
            pincode="281001",
            ro_model="ARI RO",
            monthly_rent=Decimal("500.00"),
            is_active=True,
        )
        self.inactive_customer = Customer.objects.create(
            user=self.inactive_user,
            name="Inactive Customer",
            phone=self.inactive_user.phone,
            address="B",
            city="Mathura",
            state="Uttar Pradesh",
            pincode="281001",
            ro_model="ARI RO",
            monthly_rent=Decimal("500.00"),
            is_active=False,
        )
        self.client.force_authenticate(self.admin)

    def _offer_payload(self, audience, **extra):
        return {
            "title": f"{audience} Offer",
            "message": "Special offer",
            "audience": audience,
            "offer_scope": "PURCHASE",
            "discount_type": "PERCENT",
            "discount_value": "10",
            "minimum_amount": "0",
            "max_discount": "0",
            "auto_apply": True,
            "action": "SHOP",
            **extra,
        }

    def test_inactive_customer_audience_delivers_only_to_inactive_customer(self):
        response = self.client.post(
            "/api/auth/admin/offers/",
            self._offer_payload("INACTIVE"),
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["delivered"], 1)
        self.assertTrue(UserNotification.objects.filter(
            user=self.inactive_user,
            title="INACTIVE Offer",
        ).exists())
        self.assertFalse(UserNotification.objects.filter(
            user=self.active_user,
            title="INACTIVE Offer",
        ).exists())

        self.client.force_authenticate(self.inactive_user)
        engagement = self.client.get("/api/auth/customer-engagement/")
        self.assertEqual(engagement.status_code, 200)
        self.assertTrue(any(item["title"] == "INACTIVE Offer" for item in engagement.data["items"]))

        self.client.force_authenticate(self.active_user)
        engagement = self.client.get("/api/auth/customer-engagement/")
        self.assertFalse(any(item["title"] == "INACTIVE Offer" for item in engagement.data["items"]))

    def test_single_inactive_customer_can_receive_targeted_offer(self):
        response = self.client.post(
            "/api/auth/admin/offers/",
            self._offer_payload(
                "TARGETED",
                target_customer_id=self.inactive_customer.id,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["target_customer_id"], self.inactive_customer.id)
        self.assertEqual(response.data["delivered"], 1)

        offer = CustomerEngagement.objects.get(pk=response.data["id"])
        self.assertEqual(offer.audience, "TARGETED")
        self.assertEqual(offer.target_user, self.inactive_user)

    def test_active_audience_does_not_apply_to_inactive_customer(self):
        CustomerEngagement.objects.create(
            kind="OFFER",
            audience="ACTIVE",
            title="Active Rent Offer",
            message="10 percent off",
            discount_type="PERCENT",
            discount_value=Decimal("10.00"),
            offer_scope="RENT",
            auto_apply=True,
            valid_from=timezone.now(),
        )

        self.client.force_authenticate(self.inactive_user)
        engagement = self.client.get("/api/auth/customer-engagement/")
        self.assertFalse(any(item["title"] == "Active Rent Offer" for item in engagement.data["items"]))

    def test_offer_customer_picker_includes_inactive_records(self):
        response = self.client.get("/api/auth/admin/offers/customers/")
        self.assertEqual(response.status_code, 200)
        by_id = {item["id"]: item for item in response.data["customers"]}
        self.assertIn(self.active_customer.id, by_id)
        self.assertIn(self.inactive_customer.id, by_id)
        self.assertTrue(by_id[self.active_customer.id]["is_active"])
        self.assertFalse(by_id[self.inactive_customer.id]["is_active"])
