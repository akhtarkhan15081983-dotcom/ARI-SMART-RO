from datetime import date
from decimal import Decimal

from rest_framework.test import APITestCase

from accounts.models import User
from employees.models import EmployeeProfile
from .models import CallingActivity, Customer, PublicCustomerRequest


class ProfessionalCallingDeskTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="9876500001", password="Test@123", role="CALLING", is_verified=True
        )
        self.employee = EmployeeProfile.objects.create(
            user=self.user, gender="MALE", joining_date=date(2026, 1, 1),
            designation="CALLING", salary=Decimal("18000.00"),
        )
        self.customer = Customer.objects.create(
            name="Existing Customer", phone="9876500002", address="Agra",
            city="Agra", state="UP", pincode="282001", ro_model="ARI RO",
            monthly_rent=Decimal("500.00"),
        )
        self.client.force_authenticate(self.user)

    def test_caller_can_create_new_lead(self):
        response = self.client.post("/api/customers/calling-desk/", {
            "customer_name": "Fresh Lead", "phone": "9876500003",
            "city": "Agra", "request_type": "PURCHASE", "priority": "HIGH",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        lead = PublicCustomerRequest.objects.get(pk=response.data["lead"]["id"])
        self.assertEqual(lead.assigned_caller, self.employee)
        self.assertEqual(lead.source, "CALLING_DESK")
        self.assertEqual(lead.priority, "HIGH")

    def test_existing_customer_can_be_added_without_duplicate_customer(self):
        before = Customer.objects.count()
        response = self.client.post(
            "/api/customers/calling-desk/", {"customer_id": self.customer.id}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Customer.objects.count(), before)
        self.assertEqual(response.data["lead"]["record_type"], "CUSTOMER")
        listing = self.client.get("/api/customers/calling-desk/")
        self.assertEqual(listing.status_code, 200)
        self.assertTrue(any(row["id"] == self.customer.id for row in listing.data["customers"]))

    def test_saving_call_creates_immutable_activity_history(self):
        lead = PublicCustomerRequest.objects.create(
            request_type="SERVICE", customer_name=self.customer.name,
            phone=self.customer.phone, address=self.customer.address,
            city=self.customer.city, state=self.customer.state, pincode=self.customer.pincode,
            existing_customer=self.customer, assigned_caller=self.employee,
        )
        response = self.client.patch(f"/api/customers/calling-desk/{lead.id}/", {
            "outcome": "CALLBACK", "note": "Call tomorrow after 11 AM",
            "next_follow_up_at": "2026-09-22T11:00:00+05:30", "duration_seconds": 75,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        activity = CallingActivity.objects.get(lead=lead)
        self.assertEqual(activity.caller, self.employee)
        self.assertEqual(activity.duration_seconds, 75)
        self.assertEqual(activity.outcome, "CALLBACK")
