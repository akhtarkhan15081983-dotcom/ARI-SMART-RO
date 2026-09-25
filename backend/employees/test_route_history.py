from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from tenancy.models import Company, CompanyMembership
from .location_models import EmployeeLocationPoint
from .models import EmployeeProfile


class EmployeeDayRouteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(
            name="Route Test Company",
            slug="route-test-company",
            phone="9111111111",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.engineer_user = User.objects.create_user(
            phone="9111111112",
            password="Test@12345",
            first_name="Route",
            last_name="Engineer",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.engineer_user,
            role="STAFF",
            is_active=True,
        )
        self.engineer = EmployeeProfile.objects.create(
            company=self.company,
            user=self.engineer_user,
            employee_id="EMP-ROUTE-001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            salary=Decimal("25000.00"),
            is_active=True,
        )

    def test_live_location_save_creates_history_point(self):
        captured = timezone.now().replace(microsecond=0)
        self.engineer.last_latitude = Decimal("27.1490000")
        self.engineer.last_longitude = Decimal("78.0450000")
        self.engineer.last_location_updated = captured
        self.engineer.is_online = True
        self.engineer.save(
            update_fields=[
                "last_latitude",
                "last_longitude",
                "last_location_updated",
                "is_online",
            ]
        )
        self.assertTrue(
            EmployeeLocationPoint.objects.filter(
                employee=self.engineer,
                captured_at=captured,
            ).exists()
        )

    def test_engineer_can_read_own_day_route_and_tracking_gap(self):
        now = timezone.now().replace(microsecond=0)
        EmployeeLocationPoint.objects.create(
            employee=self.engineer,
            latitude=Decimal("27.1490000"),
            longitude=Decimal("78.0450000"),
            captured_at=now - timedelta(minutes=10),
        )
        EmployeeLocationPoint.objects.create(
            employee=self.engineer,
            latitude=Decimal("27.1500000"),
            longitude=Decimal("78.0460000"),
            captured_at=now,
        )
        self.client.force_authenticate(user=self.engineer_user)
        response = self.client.get(
            f"/api/employees/day-route/?date={timezone.localdate().isoformat()}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["point_count"], 2)
        self.assertEqual(len(response.data["gaps"]), 1)
        self.assertEqual(response.data["employee"]["employee_id"], "EMP-ROUTE-001")
