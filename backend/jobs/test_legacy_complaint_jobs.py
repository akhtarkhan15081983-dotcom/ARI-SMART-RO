from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from complaints.models import Complaint
from customers.models import Customer
from employees.models import EmployeeProfile
from jobs.serializers import JobSerializer


class LegacyComplaintJobTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.engineer_user = User.objects.create_user(
            phone="9555500001",
            password="TestPassword123!",
            role="ENGINEER",
        )
        self.engineer = EmployeeProfile.objects.create(
            user=self.engineer_user,
            employee_id="LEGACY-ENG-001",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            gender="MALE",
        )
        self.customer = Customer.objects.create(
            name="Legacy Complaint Customer",
            phone="8555500001",
            address="Legacy address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="UNKNOWN",
        )

    def test_assigned_complaint_without_asset_gets_secure_job(self):
        complaint = Complaint.objects.create(
            customer=self.customer,
            engineer=self.engineer,
            complaint_type="OTHER",
            description="Legacy complaint",
            priority="NORMAL",
            scheduled_date=timezone.now(),
            status="ASSIGNED",
        )
        complaint.refresh_from_db()

        self.assertIsNotNone(complaint.job_id)
        self.assertEqual(complaint.job.job_type, "COMPLAINT")
        self.assertEqual(complaint.job.status, "ASSIGNED")
        self.assertEqual(complaint.job.engineer_id, self.engineer.id)
        self.assertIsNone(complaint.job.ro_asset_id)

        data = JobSerializer(complaint.job).data
        self.assertEqual(data["asset_id"], "")
