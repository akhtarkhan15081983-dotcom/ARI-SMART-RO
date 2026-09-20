from datetime import date
from decimal import Decimal

from rest_framework.test import APITestCase

from accounts.models import User
from assets.models import ROAsset
from customers.models import Customer
from employees.models import EmployeeProfile
from products.models import ProductCategory, ROModel


class WalkInInstallationAmountTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="9222222201",
            password="Strong@Test1",
            role="ENGINEER",
            first_name="Installer",
        )
        self.employee = EmployeeProfile.objects.create(
            user=self.user,
            employee_id="EMP-INSTALL-1",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            gender="MALE",
            salary=Decimal("25000"),
        )
        category = ProductCategory.objects.create(name="Installation Split Test")
        self.model = ROModel.objects.create(
            category=category,
            model_name="Split Test RO",
            capacity="12 LPH",
            business_type="RENT",
        )
        self.asset = ROAsset.objects.create(ro_model=self.model)
        self.client.force_authenticate(self.user)

    def test_three_thousand_is_split_into_600_installation_and_2400_security(self):
        response = self.client.post(
            "/api/customers/walk-in/",
            {
                "name": "Amount Split Customer",
                "phone": "9333333301",
                "alternate_phone": "",
                "address": "Test Address",
                "area": "Test Area",
                "city": "Agra",
                "state": "Uttar Pradesh",
                "pincode": "282001",
                "ro_model": self.model.id,
                "asset_id": self.asset.id,
                "total_amount_received": "3000",
                "monthly_rent": "300",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        customer = Customer.objects.get(pk=response.data["customer_id"])
        self.assertEqual(customer.installation_charge, Decimal("600.00"))
        self.assertEqual(customer.security_deposit, Decimal("2400.00"))

    def test_amount_below_600_is_rejected(self):
        response = self.client.post(
            "/api/customers/walk-in/",
            {
                "name": "Low Amount Customer",
                "phone": "9333333302",
                "address": "Test Address",
                "area": "Test Area",
                "city": "Agra",
                "state": "Uttar Pradesh",
                "pincode": "282001",
                "ro_model": self.model.id,
                "asset_id": self.asset.id,
                "total_amount_received": "500",
                "monthly_rent": "300",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Customer.objects.filter(phone="9333333302").exists())
