from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from assets.models import ROAsset
from complaints.models import Complaint
from customers.models import Customer
from employees.models import EmployeeProfile
from products.models import ProductCategory, ROModel
from service.models import Service
from jobs.models import JobActivityLog, JobMedia, JobSignature
from jobs.services import NO_PARTS_ACTIVITY, change_job_status


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

    def _complaint(self):
        complaint = Complaint.objects.create(
            customer=self.customer,
            engineer=self.engineer,
            complaint_type="WATER_LEAKAGE",
            description="Leakage",
            scheduled_date=timezone.now(),
            status="ASSIGNED",
        )
        complaint.refresh_from_db()
        return complaint

    def _service(self):
        service = Service.objects.create(
            customer=self.customer,
            engineer=self.engineer,
            ro_asset=self.asset,
            service_type="REGULAR",
            scheduled_date=timezone.now(),
            status="PENDING",
        )
        service.refresh_from_db()
        return service

    def _photo(self, job, description):
        return JobMedia.objects.create(
            job=job,
            media_type="PHOTO",
            description=description,
            file=SimpleUploadedFile(
                f"{description.replace(' ', '-').lower()}.jpg",
                b"proof-photo",
                content_type="image/jpeg",
            ),
        )

    def _signature(self, job):
        return JobSignature.objects.create(
            job=job,
            customer_name="Workflow Customer",
            signature=SimpleUploadedFile(
                "signature.png",
                b"signature-proof",
                content_type="image/png",
            ),
        )

    def _advance_to_arrived(self, job):
        change_job_status(job, "ACCEPTED")
        change_job_status(job, "ON_THE_WAY")
        change_job_status(job, "ARRIVED")

    def test_assigned_complaint_creates_linked_complaint_job(self):
        complaint = self._complaint()
        self.assertIsNotNone(complaint.job_id)
        self.assertEqual(complaint.job.job_type, "COMPLAINT")
        self.assertEqual(complaint.job.engineer_id, self.engineer.id)
        self.assertEqual(complaint.job.ro_asset_id, self.asset.id)
        self.assertEqual(complaint.job.status, "ASSIGNED")

    def test_source_complaint_cannot_start_or_resolve_job(self):
        complaint = self._complaint()
        complaint.status = "IN_PROGRESS"
        with self.assertRaises(ValidationError):
            complaint.save()
        complaint.refresh_from_db()
        complaint.job.refresh_from_db()
        self.assertEqual(complaint.status, "ASSIGNED")
        self.assertEqual(complaint.job.status, "ASSIGNED")

        complaint.status = "RESOLVED"
        complaint.resolution = "Attempted bypass"
        with self.assertRaises(ValidationError):
            complaint.save()
        complaint.job.refresh_from_db()
        self.assertEqual(complaint.job.status, "ASSIGNED")

    def test_source_service_cannot_start_or_complete_job(self):
        service = self._service()
        service.status = "IN_PROGRESS"
        with self.assertRaises(ValidationError):
            service.save()
        service.refresh_from_db()
        service.job.refresh_from_db()
        self.assertEqual(service.status, "PENDING")
        self.assertEqual(service.job.status, "ASSIGNED")

        service.status = "COMPLETED"
        with self.assertRaises(ValidationError):
            service.save()
        service.job.refresh_from_db()
        self.assertEqual(service.job.status, "ASSIGNED")

    def test_field_work_cannot_start_without_before_photo(self):
        service = self._service()
        job = service.job
        self._advance_to_arrived(job)
        with self.assertRaisesMessage(
            ValueError,
            "Cannot start work: before photo is missing.",
        ):
            change_job_status(job, "IN_PROGRESS")

    def test_field_work_completion_requires_parts_or_no_parts_declaration(self):
        service = self._service()
        job = service.job
        self._advance_to_arrived(job)
        self._photo(job, "Before Photo")
        change_job_status(job, "IN_PROGRESS")
        self._photo(job, "After Photo")
        job.otp_verified = True
        job.save(update_fields=["otp_verified"])
        self._signature(job)

        with self.assertRaisesMessage(
            ValueError,
            "Cannot complete job: scan every used part or confirm that no part was used.",
        ):
            change_job_status(job, "COMPLETED")

    def test_valid_no_parts_proof_completes_service_and_syncs_source(self):
        service = self._service()
        job = service.job
        self._advance_to_arrived(job)
        self._photo(job, "Before Photo")
        change_job_status(job, "IN_PROGRESS")
        JobActivityLog.objects.create(
            job=job,
            engineer=self.engineer,
            activity=NO_PARTS_ACTIVITY,
            remarks="No replacement part required.",
        )
        self._photo(job, "After Photo")
        job.otp_verified = True
        job.save(update_fields=["otp_verified"])
        self._signature(job)

        change_job_status(job, "COMPLETED")
        job.refresh_from_db()
        service.refresh_from_db()
        self.assertEqual(job.status, "COMPLETED")
        self.assertEqual(service.status, "COMPLETED")
        self.assertIsNotNone(service.completed_date)

    def test_valid_no_parts_proof_resolves_complaint(self):
        complaint = self._complaint()
        job = complaint.job
        self._advance_to_arrived(job)
        self._photo(job, "Before Photo")
        change_job_status(job, "IN_PROGRESS")
        JobActivityLog.objects.create(
            job=job,
            engineer=self.engineer,
            activity=NO_PARTS_ACTIVITY,
        )
        self._photo(job, "After Photo")
        job.otp_verified = True
        job.save(update_fields=["otp_verified"])
        self._signature(job)

        change_job_status(job, "COMPLETED")
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, "RESOLVED")
        self.assertIsNotNone(complaint.resolved_date)
