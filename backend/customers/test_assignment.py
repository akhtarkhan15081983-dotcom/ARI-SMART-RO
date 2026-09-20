from datetime import date
from decimal import Decimal

from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Customer
from employees.models import EmployeeProfile


class CustomerAssignmentTests(APITestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            phone="9444444401",
            password="Strong@Test1",
            role="MANAGER",
            first_name="Manager",
        )
        self.engineer_user = User.objects.create_user(
            phone="9444444402",
            password="Strong@Test1",
            role="ENGINEER",
            first_name="Engineer",
        )
        self.engineer = EmployeeProfile.objects.create(
            user=self.engineer_user,
            employee_id="EMP-ASSIGN-1",
            joining_date=date.today(),
            designation="ENGINEER",
            gender="MALE",
            salary=Decimal("25000"),
        )
        self.customer = Customer.objects.create(
            name="No Job Customer",
            phone="9444444403",
            address="Agra",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI RO",
        )

    def test_assign_customer_without_existing_job_returns_success(self):
        self.client.force_authenticate(self.manager)
        response = self.client.post(
            f"/api/customers/{self.customer.id}/assign/",
            {"employee_id": self.engineer.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertIsNone(response.data["job_id"])

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.assigned_engineer_id, self.engineer.id)
