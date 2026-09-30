from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from accounts.models import User, UserNotification
from customers.models import Customer
from products.models import ProductCategory, ROModel
from tenancy.models import Company, CompanyMembership

from .models import ROAlarm, ROAsset


class ROAlarmCenterTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="ARI Test",
            slug="ari-test-ro-alarm",
            phone="9999999999",
        )
        self.admin = User.objects.create_user(
            phone="9000000001",
            password="AdminPass123!",
            first_name="Admin",
            role="ADMIN",
            is_verified=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.admin,
            role="ADMIN",
        )
        self.customer_user = User.objects.create_user(
            phone="9000000002",
            password="CustomerPass123!",
            first_name="Customer",
            role="CUSTOMER",
            is_verified=True,
        )
        self.customer = Customer.objects.create(
            company=self.company,
            user=self.customer_user,
            name="Alarm Customer",
            phone=self.customer_user.phone,
            address="Test address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="Alarm RO",
        )
        category = ProductCategory.objects.create(name="Alarm Test Category")
        ro_model = ROModel.objects.create(
            category=category,
            model_name="Alarm Test RO",
            capacity="12 LPH",
            business_type="RENT",
            available_for_rent=True,
        )
        self.asset = ROAsset.objects.create(
            ro_model=ro_model,
            serial_number="ALARM-TEST-001",
            status="INSTALLED",
            current_customer=self.customer,
            next_filter_change_date=timezone.localdate(),
        )
        self.client = APIClient()

    def test_customer_can_report_alarm_for_own_ro(self):
        self.client.force_authenticate(self.customer_user)
        response = self.client.post(
            "/api/assets/ro-alarms/",
            {
                "ro_asset": self.asset.id,
                "alarm_type": "LEAKAGE",
                "message": "Leakage near inlet pipe.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        alarm = ROAlarm.objects.get()
        self.assertEqual(alarm.source, "CUSTOMER")
        self.assertEqual(alarm.severity, "HIGH")
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.customer_user,
                event_key=f"ro-alarm:{alarm.id}:open",
            ).exists()
        )
        self.assertTrue(
            UserNotification.objects.filter(
                user=self.admin,
                event_key=f"ro-alarm:{alarm.id}:open",
            ).exists()
        )

    def test_customer_cannot_report_alarm_for_another_company_ro(self):
        other_company = Company.objects.create(
            name="Other",
            slug="other-ro-alarm",
            phone="8888888888",
        )
        other_customer = Customer.objects.create(
            company=other_company,
            name="Other Customer",
            phone="8111111111",
            address="Other",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            ro_model="Other RO",
        )
        other_asset = ROAsset.objects.create(
            ro_model=self.asset.ro_model,
            serial_number="ALARM-TEST-OTHER",
            status="INSTALLED",
            current_customer=other_customer,
        )
        self.client.force_authenticate(self.customer_user)
        response = self.client.post(
            "/api/assets/ro-alarms/",
            {
                "ro_asset": other_asset.id,
                "alarm_type": "NOISE",
                "message": "Noise",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(ROAlarm.objects.filter(ro_asset=other_asset).exists())

    def test_filter_due_refresh_is_idempotent(self):
        self.client.force_authenticate(self.admin)

        first = self.client.post(
            "/api/assets/ro-alarms/refresh/",
            {"horizon_days": 7},
            format="json",
        )
        second = self.client.post(
            "/api/assets/ro-alarms/refresh/",
            {"horizon_days": 7},
            format="json",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["created"], 1)
        self.assertEqual(second.data["created"], 0)
        self.assertEqual(
            ROAlarm.objects.filter(
                ro_asset=self.asset,
                alarm_type="FILTER_DUE",
            ).count(),
            1,
        )

    def test_customer_cannot_run_system_refresh(self):
        self.client.force_authenticate(self.customer_user)
        response = self.client.post(
            "/api/assets/ro-alarms/refresh/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_can_acknowledge_and_resolve_alarm(self):
        alarm = ROAlarm.objects.create(
            ro_asset=self.asset,
            alarm_type="LOW_FLOW",
            source="CUSTOMER",
            title="Low RO water flow reported",
        )
        self.client.force_authenticate(self.admin)

        acknowledged = self.client.post(
            f"/api/assets/ro-alarms/{alarm.id}/status/",
            {"action": "ACKNOWLEDGE"},
            format="json",
        )
        self.assertEqual(acknowledged.status_code, 200)
        alarm.refresh_from_db()
        self.assertEqual(alarm.status, "ACKNOWLEDGED")
        self.assertEqual(alarm.acknowledged_by, self.admin)

        resolved = self.client.post(
            f"/api/assets/ro-alarms/{alarm.id}/status/",
            {"action": "RESOLVE"},
            format="json",
        )
        self.assertEqual(resolved.status_code, 200)
        alarm.refresh_from_db()
        self.assertEqual(alarm.status, "RESOLVED")
        self.assertEqual(alarm.resolved_by, self.admin)
        self.assertIsNotNone(alarm.resolved_at)
