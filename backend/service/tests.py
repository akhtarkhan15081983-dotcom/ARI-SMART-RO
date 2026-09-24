from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from assets.models import ROAsset
from customers.models import Customer
from employees.models import EmployeeProfile
from products.models import ProductCategory, ROModel

from .models import Service


class ServiceAssignmentTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.engineer_user = User.objects.create_user(
            phone="9333300001",
            password="TestPassword123!",
            role="ENGINEER",
        )
        self.other_engineer_user = User.objects.create_user(
            phone="9333300002",
            password="TestPassword123!",
            role="ENGINEER",
        )

        self.engineer = EmployeeProfile.objects.create(
            user=self.engineer_user,
            employee_id="SER-ENG-001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )
        self.other_engineer = EmployeeProfile.objects.create(
            user=self.other_engineer_user,
            employee_id="SER-ENG-002",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )

        category = ProductCategory.objects.create(
            name="Service Assignment Category",
        )
        model = ROModel.objects.create(
            category=category,
            model_name="Service Assignment RO",
            capacity="12 LPH",
            business_type="RENT",
            monthly_rent=Decimal("1000.00"),
            installation_charge=Decimal("600.00"),
            security_deposit=Decimal("1000.00"),
            selling_price=Decimal("10000.00"),
            warranty_months=12,
        )
        self.customer = Customer.objects.create(
            name="Service Assignment Customer",
            phone="8333300001",
            address="Service Address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="Service Assignment RO",
        )
        self.asset = ROAsset.objects.create(
            ro_model=model,
            serial_number="SER-ASSET-001",
            status="ASSIGNED",
            current_customer=self.customer,
        )

        # Field execution starts from PENDING and is advanced only by the
        # linked secure Job workflow. Creating records directly IN_PROGRESS
        # is intentionally rejected by the anti-fraud signal.
        self.service = Service.objects.create(
            customer=self.customer,
            engineer=self.engineer,
            ro_asset=self.asset,
            service_type="REGULAR",
            scheduled_date=timezone.now(),
            status="PENDING",
        )
        self.other_service = Service.objects.create(
            customer=self.customer,
            engineer=self.other_engineer,
            ro_asset=self.asset,
            service_type="REGULAR",
            scheduled_date=timezone.now(),
            status="PENDING",
        )

        self.client = APIClient()
        self.client.force_authenticate(self.engineer_user)

    def test_engineer_list_contains_only_assigned_service(self):
        response = self.client.get(reverse("service-list"))
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.data}
        self.assertEqual(ids, {self.service.id})

    def test_assigned_engineer_cannot_bypass_secure_job_completion(self):
        response = self.client.post(
            reverse("service-complete", kwargs={"pk": self.service.pk}),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.service.refresh_from_db()
        self.service.job.refresh_from_db()
        self.assertEqual(self.service.status, "PENDING")
        self.assertEqual(self.service.job.status, "ASSIGNED")
        self.assertIsNone(self.service.completed_date)

    def test_engineer_cannot_complete_another_engineers_service(self):
        response = self.client.post(
            reverse("service-complete", kwargs={"pk": self.other_service.pk}),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.other_service.refresh_from_db()
        self.assertEqual(self.other_service.status, "PENDING")
