from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from assets.models import ROAsset
from customers.models import Customer
from jobs.models import Job
from products.models import ProductCategory, ROModel

from .models import EmployeeProfile


class EmployeeIdentityTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.engineer_user = User.objects.create_user(
            phone="9666600001",
            password="Strong@Test1",
            first_name="Ravi",
            last_name="Engineer",
            role="ENGINEER",
            is_verified=True,
        )
        self.engineer = EmployeeProfile.objects.create(
            user=self.engineer_user,
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            salary=Decimal("25000.00"),
            address="Private employee home address",
            city="Agra",
            state="Uttar Pradesh",
            face_enrollment_verified=True,
            attendance_device_id="DEVICE-001",
            id_card_issued_at=timezone.now(),
            id_card_valid_until=timezone.localdate() + timedelta(days=365),
        )

        self.customer_user = User.objects.create_user(
            phone="9666600002",
            password="Strong@Test1",
            first_name="Customer",
            role="CUSTOMER",
            is_verified=True,
        )
        self.customer = Customer.objects.create(
            user=self.customer_user,
            name="Customer One",
            phone=self.customer_user.phone,
            address="Customer Address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="Identity RO",
            monthly_rent=Decimal("1000.00"),
        )

        category = ProductCategory.objects.create(name="Identity Test Category")
        model = ROModel.objects.create(
            category=category,
            model_name="Identity Test RO",
            capacity="12 LPH",
            business_type="RENT",
            monthly_rent=Decimal("1000.00"),
            installation_charge=Decimal("500.00"),
            security_deposit=Decimal("1000.00"),
            selling_price=Decimal("10000.00"),
            warranty_months=12,
        )
        asset = ROAsset.objects.create(
            ro_model=model,
            serial_number="IDENTITY-ASSET-001",
            status="ASSIGNED",
            current_customer=self.customer,
        )
        self.job = Job.objects.create(
            customer=self.customer,
            ro_asset=asset,
            engineer=self.engineer,
            job_type="SERVICE",
            priority="MEDIUM",
            scheduled_date=timezone.now() + timedelta(hours=2),
            status="ASSIGNED",
        )

    def test_employee_verification_codes_are_generated_and_unique(self):
        User = get_user_model()
        other_user = User.objects.create_user(
            phone="9666600003",
            password="Strong@Test1",
            first_name="Other",
            role="ENGINEER",
            is_verified=True,
        )
        other = EmployeeProfile.objects.create(
            user=other_user,
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )
        self.assertTrue(self.engineer.public_verification_code)
        self.assertTrue(other.public_verification_code)
        self.assertNotEqual(
            self.engineer.public_verification_code,
            other.public_verification_code,
        )

    def test_employee_id_card_does_not_expose_private_hr_data(self):
        self.client.force_authenticate(self.engineer_user)
        response = self.client.get("/api/employees/id-card/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["employee_id"], self.engineer.employee_id)
        self.assertEqual(
            response.data["verification_code"],
            self.engineer.public_verification_code,
        )
        self.assertNotIn("salary", response.data)
        self.assertNotIn("address", response.data)
        self.assertNotIn("phone", response.data)

    def test_customer_sees_only_assigned_engineer_official_identity(self):
        self.client.force_authenticate(self.customer_user)
        response = self.client.get("/api/jobs/customer-assigned-engineer/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["available"])
        engineer = response.data["engineer"]
        self.assertEqual(engineer["employee_id"], self.engineer.employee_id)
        self.assertEqual(engineer["name"], "Ravi Engineer")
        self.assertNotIn("phone", engineer)
        self.assertNotIn("salary", engineer)
        self.assertNotIn("address", engineer)
        self.assertEqual(response.data["job_number"], self.job.job_id)

    def test_customer_without_active_job_gets_no_engineer_identity(self):
        User = get_user_model()
        other_customer_user = User.objects.create_user(
            phone="9666600004",
            password="Strong@Test1",
            first_name="No Job",
            role="CUSTOMER",
            is_verified=True,
        )
        Customer.objects.create(
            user=other_customer_user,
            name="No Job Customer",
            phone=other_customer_user.phone,
            address="Other Address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282002",
            ro_model="Identity RO",
        )
        self.client.force_authenticate(other_customer_user)
        response = self.client.get("/api/jobs/customer-assigned-engineer/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["available"])
        self.assertEqual(response.data["reason"], "NO_ACTIVE_JOB")

    def test_verify_id_returns_only_safe_public_employee_fields(self):
        self.client.force_authenticate(self.customer_user)
        response = self.client.get(
            f"/api/employees/verify-id/{self.engineer.public_verification_code}/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["verified"])
        employee = response.data["employee"]
        self.assertEqual(employee["employee_id"], self.engineer.employee_id)
        self.assertNotIn("phone", employee)
        self.assertNotIn("salary", employee)
        self.assertNotIn("address", employee)
