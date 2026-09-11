from datetime import date
from decimal import Decimal

from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Customer
from employees.models import EmployeeProfile
from .models import Complaint


class ComplaintWorkflowTests(APITestCase):
    def setUp(self):
        self.office = User.objects.create_user(phone="9222222201", password="test", role="OFFICE")
        self.engineer_user = User.objects.create_user(
            phone="9222222202", password="test", role="ENGINEER", first_name="Service", last_name="Engineer"
        )
        self.engineer = EmployeeProfile.objects.create(
            user=self.engineer_user,
            employee_id="EMP-COMPLAINT-1",
            joining_date=date.today(),
            designation="ENGINEER",
            gender="MALE",
        )
        self.customer = Customer.objects.create(
            name="Saved Location Customer",
            phone="8222222201",
            address="Test address",
            city="Bareilly",
            state="Uttar Pradesh",
            pincode="243001",
            ro_model="ARI RO",
            latitude=Decimal("28.3670000"),
            longitude=Decimal("79.4300000"),
        )

    def test_office_complaint_copies_saved_location_and_returns_engineer_phone(self):
        self.client.force_authenticate(self.office)
        response = self.client.post("/api/complaints/create/", {
            "customer": self.customer.id,
            "engineer": self.engineer.id,
            "complaint_type": "WATER_LEAKAGE",
            "description": "Leakage under purifier",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        complaint = Complaint.objects.get(pk=response.data["id"])
        self.assertEqual(complaint.latitude, self.customer.latitude)
        self.assertEqual(complaint.longitude, self.customer.longitude)
        self.assertEqual(response.data["engineer_phone"], self.engineer_user.phone)