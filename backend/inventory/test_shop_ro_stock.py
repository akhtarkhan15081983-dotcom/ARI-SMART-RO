from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from products.models import ProductCategory, ROModel


class ShopROInventoryVisibilityTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            phone="9888811011",
            password="StrongPass@123",
            role="ADMIN",
            is_verified=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        category = ProductCategory.objects.create(name="Inventory Shop RO")
        self.visible = ROModel.objects.create(
            category=category,
            model_name="ARI Max Pro 12L",
            capacity="12 LPH",
            business_type="SALE",
            available_for_sale=True,
            available_for_rent=True,
            selling_price=Decimal("14999.00"),
            monthly_rent=Decimal("900.00"),
            stock_quantity=7,
            is_active=True,
        )
        ROModel.objects.create(
            category=category,
            model_name="Inactive Test RO",
            capacity="12 LPH",
            business_type="SALE",
            stock_quantity=99,
            is_active=False,
        )

    def test_inventory_summary_surfaces_shop_ro_stock_without_part_duplication(self):
        response = self.client.get("/api/inventory/workflow/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["shop_ro_models"], 1)
        self.assertEqual(response.data["summary"]["shop_ro_units"], 7)
        self.assertEqual(len(response.data["shop_ro_stock"]), 1)
        row = response.data["shop_ro_stock"][0]
        self.assertEqual(row["id"], self.visible.id)
        self.assertEqual(row["model_name"], "ARI Max Pro 12L")
        self.assertEqual(row["stock_quantity"], 7)
        self.assertTrue(row["available_for_sale"])
        self.assertTrue(row["available_for_rent"])
