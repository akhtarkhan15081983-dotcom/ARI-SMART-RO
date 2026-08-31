from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from employees.models import EmployeeProfile

from .models import Customer, CustomerLocationLog


class CustomerLocationCaptureAPITests(APITestCase):
    def setUp(self):
        self.engineer_user = User.objects.create_user(
            phone="9000000001",
            password="test-pass",
            first_name="Assigned",
            role="ENGINEER",
        )
        self.engineer = EmployeeProfile.objects.create(
            user=self.engineer_user,
            employee_id="EMP-TEST-1",
            gender="MALE",
            joining_date=date.today(),
            designation="ENGINEER",
        )
        self.other_user = User.objects.create_user(
            phone="9000000002",
            password="test-pass",
            first_name="Other",
            role="ENGINEER",
        )
        EmployeeProfile.objects.create(
            user=self.other_user,
            employee_id="EMP-TEST-2",
            gender="MALE",
            joining_date=date.today(),
            designation="ENGINEER",
        )
        self.office_user = User.objects.create_user(
            phone="9000000003",
            password="test-pass",
            first_name="Office",
            role="OFFICE",
        )
        self.customer = Customer.objects.create(
            name="Location Customer",
            phone="8000000001",
            address="Test address",
            city="Bareilly",
            state="Uttar Pradesh",
            pincode="243001",
            ro_model="ARI Test RO",
            assigned_engineer=self.engineer,
        )
        self.url = reverse("customer-capture-location", args=[self.customer.pk])

    def test_assigned_engineer_can_capture_location_once(self):
        self.client.force_authenticate(self.engineer_user)
        response = self.client.post(
            self.url,
            {
                "latitude": "28.3670000",
                "longitude": "79.4300000",
                "accuracy": "8.50",
                "source": "WORK_CALENDAR",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.customer.refresh_from_db()
        self.assertEqual(str(self.customer.latitude), "28.3670000")
        self.assertEqual(CustomerLocationLog.objects.count(), 1)
        self.assertEqual(CustomerLocationLog.objects.get().captured_by, self.engineer)

        second_response = self.client.post(
            self.url,
            {"latitude": "28.4000000", "longitude": "79.5000000"},
            format="json",
        )
        self.assertEqual(second_response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(CustomerLocationLog.objects.count(), 1)

    def test_other_engineer_cannot_capture_location(self):
        self.client.force_authenticate(self.other_user)
        response = self.client.post(
            self.url,
            {"latitude": "28.3670000", "longitude": "79.4300000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CustomerLocationLog.objects.count(), 0)

    def test_office_user_cannot_capture_location(self):
        self.client.force_authenticate(self.office_user)
        response = self.client.post(
            self.url,
            {"latitude": "28.3670000", "longitude": "79.4300000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CustomerLocationLog.objects.count(), 0)
