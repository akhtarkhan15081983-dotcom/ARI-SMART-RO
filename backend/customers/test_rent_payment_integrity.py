from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from customers.models import Customer, CustomerRentHistory, CustomerRentPayment
from employees.models import EmployeeProfile
from jobs.models import ClientActionReceipt
from tenancy.models import Company, CompanyMembership


class RentPaymentIntegrityTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="Rent Integrity Tenant",
            slug="rent-integrity-tenant",
            phone="9000000301",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9222222301",
            password="Strong@123",
            role="ADMIN",
            is_verified=True,
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.admin,
            role="ADMIN",
            is_active=True,
        )
        engineer_user = User.objects.create_user(
            phone="9222222302",
            password="Strong@123",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        self.engineer = EmployeeProfile.objects.create(
            company=self.company,
            user=engineer_user,
            employee_id="RENT-ENG-1",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )
        self.customer = Customer.objects.create(
            company=self.company,
            name="Rent Integrity Customer",
            phone="9333333301",
            address="Test Address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI RENT TEST",
            monthly_rent=Decimal("900.00"),
            installation_date=timezone.localdate(),
            assigned_engineer=self.engineer,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def _post(self, amount, action_id):
        return self.client.post(
            "/api/customers/rent-management/payment/",
            {
                "customer_id": self.customer.id,
                "amount": str(amount),
                "payment_mode": "CASH",
            },
            format="json",
            HTTP_X_ARI_ACTION_ID=action_id,
        )

    def test_partial_payment_updates_single_month_ledger_consistently(self):
        response = self._post("300.00", "rent-partial-001")
        self.assertEqual(response.status_code, 201)

        month = timezone.localdate().replace(day=1)
        rent = CustomerRentHistory.objects.get(customer=self.customer, rent_month=month)
        self.assertEqual(rent.expected_rent, Decimal("900.00"))
        self.assertEqual(rent.paid_amount, Decimal("300.00"))
        self.assertEqual(CustomerRentPayment.objects.filter(customer=self.customer).count(), 1)
        payment = CustomerRentPayment.objects.get(customer=self.customer)
        self.assertEqual(payment.amount, Decimal("300.00"))
        self.assertEqual(response.data["rent"]["balance"], 600.0)

    def test_overpayment_rolls_back_and_does_not_consume_action_id(self):
        action_id = "rent-overpay-retry-001"
        rejected = self._post("99999.00", action_id)
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(CustomerRentPayment.objects.filter(customer=self.customer).count(), 0)
        self.assertFalse(
            ClientActionReceipt.objects.filter(user=self.admin, action_id=action_id).exists()
        )

        accepted = self._post("900.00", action_id)
        self.assertEqual(accepted.status_code, 201)
        self.assertEqual(CustomerRentPayment.objects.filter(customer=self.customer).count(), 1)
        receipt = ClientActionReceipt.objects.get(user=self.admin, action_id=action_id)
        self.assertEqual(receipt.action_type, "RENT_PAYMENT")
        self.assertIsNotNone(receipt.completed_at)

    def test_second_distinct_payment_cannot_exceed_remaining_balance(self):
        first = self._post("500.00", "rent-balance-001")
        self.assertEqual(first.status_code, 201)

        second = self._post("500.00", "rent-balance-002")
        self.assertEqual(second.status_code, 400)
        self.assertEqual(CustomerRentPayment.objects.filter(customer=self.customer).count(), 1)

        month = timezone.localdate().replace(day=1)
        rent = CustomerRentHistory.objects.get(customer=self.customer, rent_month=month)
        self.assertEqual(rent.paid_amount, Decimal("500.00"))
