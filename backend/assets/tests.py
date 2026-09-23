from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Customer
from products.models import ProductCategory, ROModel

from .models import ROAsset, ROAssetMovement


class ROAssetWorkflowTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone="9999999991",
            password="StrongPass123!",
            role="ADMIN",
            is_active=True,
            is_verified=True,
        )
        self.client.force_authenticate(self.admin)
        self.category = ProductCategory.objects.create(name="Domestic RO", is_active=True)
        self.model = ROModel.objects.create(
            category=self.category,
            model_name="ARI Test RO",
            capacity="12 LPH",
            business_type="SALE",
            available_for_sale=True,
            available_for_rent=True,
            selling_price=Decimal("8500.00"),
            monthly_rent=Decimal("450.00"),
            installation_charge=Decimal("600.00"),
            security_deposit=Decimal("2400.00"),
            stock_quantity=0,
            is_active=True,
        )
        self.customer = Customer.objects.create(
            name="Test Customer",
            phone="9999999992",
            address="Test Address",
            city="Aligarh",
            state="Uttar Pradesh",
            pincode="202001",
            ro_model="",
            ownership_type="RENTAL",
        )

    def test_bulk_receive_creates_traceable_assets_and_updates_stock(self):
        response = self.client.post(
            "/api/assets/workflow/receive/",
            {
                "ro_model": self.model.id,
                "serial_numbers": ["RO-T-001", "RO-T-002"],
                "purchase_invoice": "INV-50",
                "purchase_price": "5000.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["received"], 2)
        self.model.refresh_from_db()
        self.assertEqual(self.model.stock_quantity, 2)
        self.assertEqual(ROAsset.objects.filter(status="WAREHOUSE").count(), 2)
        self.assertEqual(ROAssetMovement.objects.filter(action="RECEIVED").count(), 2)

    def test_rental_allocate_return_and_restock_is_atomic(self):
        asset = ROAsset.objects.create(
            ro_model=self.model,
            serial_number="RO-R-001",
            status="WAREHOUSE",
        )
        self.model.stock_quantity = 1
        self.model.save(update_fields=["stock_quantity"])

        allocated = self.client.post(
            f"/api/assets/workflow/{asset.id}/allocate/",
            {"customer_id": self.customer.id, "deployment_type": "RENT"},
            format="json",
        )
        self.assertEqual(allocated.status_code, 200)
        asset.refresh_from_db()
        self.model.refresh_from_db()
        self.customer.refresh_from_db()
        self.assertEqual(asset.status, "ASSIGNED")
        self.assertEqual(asset.deployment_type, "RENT")
        self.assertEqual(asset.current_customer_id, self.customer.id)
        self.assertEqual(self.model.stock_quantity, 0)
        self.assertEqual(self.customer.ownership_type, "RENTAL")
        self.assertEqual(self.customer.monthly_rent, Decimal("450.00"))

        duplicate = self.client.post(
            f"/api/assets/workflow/{asset.id}/allocate/",
            {"customer_id": self.customer.id, "deployment_type": "SALE"},
            format="json",
        )
        self.assertEqual(duplicate.status_code, 409)

        returned = self.client.post(
            f"/api/assets/workflow/{asset.id}/return/",
            {"remarks": "Customer return"},
            format="json",
        )
        self.assertEqual(returned.status_code, 200)
        asset.refresh_from_db()
        self.assertEqual(asset.status, "RETURNED")

        restocked = self.client.post(
            f"/api/assets/workflow/{asset.id}/restock/",
            {"remarks": "QC passed"},
            format="json",
        )
        self.assertEqual(restocked.status_code, 200)
        asset.refresh_from_db()
        self.model.refresh_from_db()
        self.assertEqual(asset.status, "WAREHOUSE")
        self.assertEqual(asset.deployment_type, "")
        self.assertIsNone(asset.current_customer_id)
        self.assertEqual(self.model.stock_quantity, 1)
        actions = list(
            ROAssetMovement.objects.filter(asset=asset).values_list("action", flat=True)
        )
        self.assertIn("RENT_ALLOCATED", actions)
        self.assertIn("RENT_RETURNED", actions)
        self.assertIn("RESTOCKED", actions)

    def test_sale_allocation_updates_customer_and_removes_available_stock(self):
        asset = ROAsset.objects.create(
            ro_model=self.model,
            serial_number="RO-S-001",
            status="WAREHOUSE",
        )
        self.model.stock_quantity = 1
        self.model.save(update_fields=["stock_quantity"])

        response = self.client.post(
            f"/api/assets/workflow/{asset.id}/allocate/",
            {"customer_id": self.customer.id, "deployment_type": "SALE"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        asset.refresh_from_db()
        self.customer.refresh_from_db()
        self.model.refresh_from_db()
        self.assertEqual(asset.deployment_type, "SALE")
        self.assertEqual(self.customer.ownership_type, "PURCHASE")
        self.assertEqual(self.customer.ro_model, self.model.model_name)
        self.assertEqual(self.model.stock_quantity, 0)
