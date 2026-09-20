from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from customers.models import Customer
from .models import CustomerEngagement, User, UserNotification


class NotificationCenterTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone="9888800001",
            password="Strong@Test1",
            first_name="Admin",
            role="ADMIN",
            is_verified=True,
        )
        self.engineer = User.objects.create_user(
            phone="9888800002",
            password="Strong@Test1",
            first_name="Engineer",
            role="ENGINEER",
            is_verified=True,
        )
        self.customer_user = User.objects.create_user(
            phone="9888800003",
            password="Strong@Test1",
            first_name="Customer",
            role="CUSTOMER",
            is_verified=True,
        )
        self.customer = Customer.objects.create(
            user=self.customer_user,
            name="Offer Customer",
            phone=self.customer_user.phone,
            address="Test Address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI Test RO",
            monthly_rent=Decimal("500.00"),
            installation_date=timezone.localdate().replace(day=1),
        )

    def test_admin_role_campaign_reaches_engineer_not_customer(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/auth/admin/notification-campaigns/",
            {
                "title": "Engineer briefing",
                "message": "Today service briefing at 10 AM.",
                "audience": "ROLE",
                "target_role": "ENGINEER",
                "category": "JOB",
                "priority": "HIGH",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["delivered"], 1)
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.engineer, title="Engineer briefing"
            ).exists()
        )
        self.assertFalse(
            UserNotification.objects.filter(
                user=self.customer_user, title="Engineer briefing"
            ).exists()
        )

    def test_customer_can_read_notification(self):
        UserNotification.objects.create(
            user=self.customer_user,
            event_key="test:customer:1",
            title="Test notification",
            message="Hello customer",
            category="GENERAL",
        )
        self.client.force_authenticate(self.customer_user)
        listing = self.client.get("/api/auth/notifications/")
        self.assertEqual(listing.status_code, 200)
        self.assertGreaterEqual(listing.data["unread_count"], 1)

        notification_id = next(
            item["id"]
            for item in listing.data["items"]
            if item["title"] == "Test notification"
        )
        marked = self.client.post(
            "/api/auth/notifications/",
            {"notification_id": notification_id},
            format="json",
        )
        self.assertEqual(marked.status_code, 200)
        self.assertTrue(
            UserNotification.objects.get(pk=notification_id).is_read
        )

    def test_auto_rent_offer_reduces_customer_current_rent(self):
        CustomerEngagement.objects.create(
            kind="OFFER",
            audience="ALL",
            title="Festival Rent Discount",
            message="20% off this month's rent",
            discount_type="PERCENT",
            discount_value=Decimal("20.00"),
            offer_scope="RENT",
            auto_apply=True,
            valid_from=timezone.now(),
            priority=90,
            action="RENT",
        )
        self.client.force_authenticate(self.customer_user)
        response = self.client.get("/api/customers/rent/")
        self.assertEqual(response.status_code, 200)
        current = response.data["current_rent"]
        self.assertEqual(Decimal(str(current["base_rent"])), Decimal("500.0"))
        self.assertEqual(Decimal(str(current["discount_amount"])), Decimal("100.0"))
        self.assertEqual(Decimal(str(current["expected_rent"])), Decimal("400.0"))
        self.assertEqual(current["applied_offer"]["title"], "Festival Rent Discount")
