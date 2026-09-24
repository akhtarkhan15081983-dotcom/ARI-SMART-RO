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
        self.office_profile = EmployeeProfile.objects.create(
            user=self.office,
            employee_id="EMP-OFFICE-1",
            joining_date=date.today(),
            designation="OFFICE",
            gender="MALE",
        )
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
            assigned_engineer=self.office_profile,
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
        self.assertEqual(complaint.status, "ASSIGNED")
        self.assertEqual(response.data["status"], "ASSIGNED")

    def test_generic_update_cannot_leave_assigned_complaint_in_new_status(self):
        complaint = Complaint.objects.create(
            customer=self.customer,
            complaint_type="OTHER",
            description="Needs assignment",
            status="NEW",
        )
        self.client.force_authenticate(self.office)
        response = self.client.patch(
            f"/api/complaints/{complaint.id}/update/",
            {"engineer": self.engineer.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        complaint.refresh_from_db()
        self.assertEqual(complaint.engineer_id, self.engineer.id)
        self.assertEqual(complaint.status, "ASSIGNED")
        self.assertEqual(response.data["status"], "ASSIGNED")

    def test_office_can_manage_all_complaints(self):
        first = Complaint.objects.create(
            customer=self.customer,
            complaint_type="WATER_LEAKAGE",
            description="First office complaint",
        )
        other_customer = Customer.objects.create(
            name="Other Customer",
            phone="8222222202",
            address="Other address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI RO",
        )
        second = Complaint.objects.create(
            customer=other_customer,
            complaint_type="OTHER",
            description="Second office complaint",
        )

        self.client.force_authenticate(self.office)
        response = self.client.get("/api/complaints/")
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.data}
        self.assertEqual(ids, {first.id, second.id})

    def test_engineer_sees_only_assigned_work(self):
        engineer_customer = Customer.objects.create(
            name="Engineer Customer",
            phone="8222222203",
            address="Engineer address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI RO",
            assigned_engineer=self.engineer,
        )
        visible = Complaint.objects.create(
            customer=engineer_customer,
            engineer=self.engineer,
            complaint_type="RO_NOT_WORKING",
        )
        Complaint.objects.create(
            customer=self.customer,
            complaint_type="OTHER",
        )

        self.client.force_authenticate(self.engineer_user)
        response = self.client.get("/api/complaints/")
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.data}
        self.assertEqual(ids, {visible.id})

    def test_engineer_does_not_see_unassigned_complaint_for_owned_customer(self):
        engineer_customer = Customer.objects.create(
            name="Engineer Owned Customer",
            phone="8222222299",
            address="Engineer address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI RO",
            assigned_engineer=self.engineer,
        )
        assigned = Complaint.objects.create(
            customer=engineer_customer,
            engineer=self.engineer,
            complaint_type="RO_NOT_WORKING",
        )
        Complaint.objects.create(
            customer=engineer_customer,
            engineer=None,
            complaint_type="OTHER",
        )

        self.client.force_authenticate(self.engineer_user)
        response = self.client.get("/api/complaints/")
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.data}
        self.assertEqual(ids, {assigned.id})
