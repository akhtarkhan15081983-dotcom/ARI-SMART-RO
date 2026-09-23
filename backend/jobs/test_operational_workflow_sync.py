from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from assets.models import ROAsset
from complaints.models import Complaint
from customers.models import Customer
from employees.models import EmployeeProfile
from products.models import ProductCategory, ROModel
from service.models import Service
from jobs.models import Job


class OperationalWorkflowSyncTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.engineer_user = User.objects.create_user(
            phone="9444400001",
            password="TestPassword123!",
            role="ENGINEER",
        )
        self.engineer = EmployeeProfile.objects.create(
            user=self.engineer_user,
            employee_id="WF-ENG-001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )
        category = ProductCategory.objects.create(name="Workflow Test Category")
        model = ROModel.objects.create(
            category=category,
            model_name="Workflow Test RO",
            capacity="12 LPH",
            business_type="RENT",
            monthly_rent=Decimal("1000.00"),
            installation_charge=Decimal("600.00"),
            security_deposit=Decimal("1000.00"),
            selling_price=Decimal("10000.00"),
            warranty_months=12,
        )
        self.customer = Customer.objects.create(
            name="Workflow Customer",
            phone="8444400001",
            address="Workflow Address",
            city="Aligarh",
            state="Uttar Pradesh",
            pincode="202001",
            ro_model="Workflow Test RO",
            assigned_engineer=self.engineer,
        )
        self.asset = ROAsset.objects.create(
            ro_model=model,
            serial_number="WF-ASSET-001",
            status="INSTALLED",
            current_customer=self.customer,
        )

    def test_assigned_complaint_creates_linked_complaint_job(self):
        complaint = Complaint.objects.create(
            customer=self.customer,
            engineer=self.engineer,
            complaint_type="WATER_LEAKAGE",
            description="Leakage",
            scheduled_date=timezone.now(),
            status="ASSIGNED",
        )
        complaint.refresh_from_db()
        self.assertIsNotNone(complaint.job_id)
        self.assertEqual(complaint.job.job_type, "COMPLAINT")
        self.assertEqual(complaint.job.engineer_id, self.engineer.id)
        self.assertEqual(complaint.job.ro_asset_id, self.asset.id)
        self.assertEqual(complaint.job.status, "ASSIGNED")

    def test_complaint_card_status_updates_linked_job(self):
        complaint = Complaint.objects.create(
            customer=self.customer,
            engineer=self.engineer,
            complaint_type="RO_NOT_WORKING",
            scheduled_date=timezone.now(),
            status="ASSIGNED",
        )
        complaint.refresh_from_db()
        complaint.status = "IN_PROGRESS"
        complaint.save()
        complaint.job.refresh_from_db()
        self.assertEqual(complaint.job.status, "IN_PROGRESS")

        complaint.status = "RESOLVED"
        complaint.resolution = "Issue fixed"
        complaint.save()
        complaint.job.refresh_from_db()
        self.assertEqual(complaint.job.status, "COMPLETED")
        self.assertIsNotNone(complaint.job.completed_at)

    def test_job_status_updates_complaint(self):
        complaint = Complaint.objects.create(
            customer=self.customer,
            engineer=self.engineer,
            complaint_type="OTHER",
            scheduled_date=timezone.now(),
            status="ASSIGNED",
        )
        complaint.refresh_from_db()
        job = complaint.job
        job.status = "IN_PROGRESS"
        job.in_progress_at = timezone.now()
        job.save()
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, "IN_PROGRESS")

        job.status = "COMPLETED"
        job.completed_at = timezone.now()
        job.save()
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, "RESOLVED")
        self.assertIsNotNone(complaint.resolved_date)

    def test_service_creates_job_and_stays_in_sync(self):
        service = Service.objects.create(
            customer=self.customer,
            engineer=self.engineer,
            ro_asset=self.asset,
            service_type="REGULAR",
            scheduled_date=timezone.now(),
            status="PENDING",
        )
        service.refresh_from_db()
        self.assertIsNotNone(service.job_id)
        self.assertEqual(service.job.job_type, "SERVICE")
        self.assertEqual(service.job.status, "ASSIGNED")

        service.status = "IN_PROGRESS"
        service.save()
        service.job.refresh_from_db()
        self.assertEqual(service.job.status, "IN_PROGRESS")

        service.status = "COMPLETED"
        service.completed_date = timezone.now()
        service.save()
        service.job.refresh_from_db()
        self.assertEqual(service.job.status, "COMPLETED")
        self.assertIsNotNone(service.job.completed_at)

        service.job.status = "CANCELLED"
        service.job.save()
        service.refresh_from_db()
        self.assertEqual(service.status, "CANCELLED")
