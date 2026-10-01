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
from jobs.models import Job
from tenancy.models import Company, CompanyMembership

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

    def test_completed_service_retry_preserves_original_completion_time(self):
        completed_at = timezone.now()
        Service.objects.filter(pk=self.service.pk).update(
            status="COMPLETED", completed_date=completed_at,
        )
        url = reverse("service-complete", kwargs={"pk": self.service.pk})
        first = self.client.post(url, {}, format="json")
        second = self.client.post(url, {}, format="json")
        self.assertEqual((first.status_code, second.status_code), (200, 200))
        self.service.refresh_from_db()
        self.assertEqual(self.service.completed_date, completed_at)


class ServiceTenantIntegrityTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.company_a = Company.objects.create(
            name="Service Tenant A",
            slug="service-tenant-a",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.company_b = Company.objects.create(
            name="Service Tenant B",
            slug="service-tenant-b",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.office_a = User.objects.create_user(
            phone="9333310001",
            password="Strong@123",
            role="OFFICE",
            is_verified=True,
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company_a,
            user=self.office_a,
            role="STAFF",
            is_active=True,
        )

        def engineer(company, phone, employee_id):
            user = User.objects.create_user(
                phone=phone,
                password="Strong@123",
                role="ENGINEER",
                is_verified=True,
                is_active=True,
            )
            CompanyMembership.objects.create(
                company=company,
                user=user,
                role="STAFF",
                is_active=True,
            )
            return EmployeeProfile.objects.create(
                company=company,
                user=user,
                employee_id=employee_id,
                gender="MALE",
                joining_date=date(2026, 1, 1),
                designation="ENGINEER",
                is_active=True,
            )

        self.engineer_a = engineer(self.company_a, "9333310002", "SER-TEN-A")
        self.engineer_b = engineer(self.company_b, "9333310003", "SER-TEN-B")

        category = ProductCategory.objects.create(name="Service Tenant Category")
        ro_model = ROModel.objects.create(
            category=category,
            model_name="Service Tenant RO",
            capacity="12 LPH",
            business_type="RENT",
            monthly_rent=Decimal("1000.00"),
            installation_charge=Decimal("600.00"),
            security_deposit=Decimal("1000.00"),
            selling_price=Decimal("10000.00"),
            warranty_months=12,
        )
        self.customer_a = Customer.objects.create(
            company=self.company_a,
            name="Service Customer A",
            phone="8333310001",
            address="A",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="Service Tenant RO",
        )
        self.customer_b = Customer.objects.create(
            company=self.company_b,
            name="Service Customer B",
            phone="8333310002",
            address="B",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="Service Tenant RO",
        )
        self.asset_a = ROAsset.objects.create(
            ro_model=ro_model,
            serial_number="SER-TEN-ASSET-A",
            status="ASSIGNED",
            current_customer=self.customer_a,
        )
        self.asset_b = ROAsset.objects.create(
            ro_model=ro_model,
            serial_number="SER-TEN-ASSET-B",
            status="ASSIGNED",
            current_customer=self.customer_b,
        )
        self.service_a = Service.objects.create(
            company=self.company_a,
            customer=self.customer_a,
            engineer=self.engineer_a,
            ro_asset=self.asset_a,
            service_type="REGULAR",
            scheduled_date=timezone.now(),
            status="PENDING",
        )
        self.service_b = Service.objects.create(
            company=self.company_b,
            customer=self.customer_b,
            engineer=self.engineer_b,
            ro_asset=self.asset_b,
            service_type="REGULAR",
            scheduled_date=timezone.now(),
            status="PENDING",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.office_a)

    def test_service_list_hides_other_tenant(self):
        response = self.client.get(reverse("service-list"))
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.data}
        self.assertIn(self.service_a.id, ids)
        self.assertNotIn(self.service_b.id, ids)

    def test_service_detail_hides_other_tenant(self):
        response = self.client.get(
            reverse("service-detail", kwargs={"pk": self.service_b.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_create_rejects_same_tenant_job_for_different_customer(self):
        other_customer = Customer.objects.create(
            company=self.company_a,
            name="Other Service Customer A",
            phone="8333310003",
            address="A2",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="Service Tenant RO",
        )
        mismatch_job = Job.objects.create(
            company=self.company_a,
            customer=other_customer,
            engineer=self.engineer_a,
            job_type="SERVICE",
            scheduled_date=timezone.now(),
        )
        response = self.client.post(
            reverse("service-create"),
            {
                "customer": self.customer_a.id,
                "engineer": self.engineer_a.id,
                "ro_asset": self.asset_a.id,
                "job": mismatch_job.id,
                "service_type": "REGULAR",
                "scheduled_date": timezone.now().isoformat(),
                "status": "PENDING",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("job", response.data)

    def test_update_rejects_cross_tenant_engineer(self):
        response = self.client.patch(
            reverse("service-update", kwargs={"pk": self.service_a.pk}),
            {"engineer": self.engineer_b.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.service_a.refresh_from_db()
        self.assertEqual(self.service_a.engineer_id, self.engineer_a.id)
