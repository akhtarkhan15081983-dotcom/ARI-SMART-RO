from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from employees.models import EmployeeProfile
from inventory.models import EngineerBagItem, InventoryItem, PartRequest
from partmaster.models import PartCategory, PartMaster
from purchase.models import Purchase, PurchaseItem, Supplier
from tenancy.models import Company, CompanyMembership


class WarehouseTenantSecurityTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.company_a = Company.objects.create(
            name="Inventory Tenant A",
            slug="inventory-tenant-a",
            phone="9000000201",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.company_b = Company.objects.create(
            name="Inventory Tenant B",
            slug="inventory-tenant-b",
            phone="9000000202",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin_a = User.objects.create_user(
            phone="9111111301",
            password="Strong@123",
            role="ADMIN",
            is_verified=True,
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company_a,
            user=self.admin_a,
            role="ADMIN",
            is_active=True,
        )
        engineer_user_a = User.objects.create_user(
            phone="9111111302",
            password="Strong@123",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company_a,
            user=engineer_user_a,
            role="STAFF",
            is_active=True,
        )
        self.engineer_a = EmployeeProfile.objects.create(
            company=self.company_a,
            user=engineer_user_a,
            employee_id="WARE-A",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )
        category = PartCategory.objects.create(name="Tenant Warehouse Parts")
        self.part = PartMaster.objects.create(
            name="Tenant Sediment",
            code="TEN-SED",
            category=category,
            is_serialized=True,
        )
        self.supplier_a = Supplier.objects.create(company=self.company_a, name="Supplier A")
        self.supplier_b = Supplier.objects.create(company=self.company_b, name="Supplier B")
        self.purchase_a = Purchase.objects.create(
            company=self.company_a,
            supplier=self.supplier_a,
            invoice_number="A-INV-1",
            invoice_date=date(2026, 9, 1),
        )
        self.purchase_b = Purchase.objects.create(
            company=self.company_b,
            supplier=self.supplier_b,
            invoice_number="B-INV-1",
            invoice_date=date(2026, 9, 1),
        )
        self.item_a = PurchaseItem.objects.create(
            company=self.company_a,
            purchase=self.purchase_a,
            part=self.part,
            quantity=1,
            purchase_price=Decimal("100.00"),
        )
        self.item_b = PurchaseItem.objects.create(
            company=self.company_b,
            purchase=self.purchase_b,
            part=self.part,
            quantity=1,
            purchase_price=Decimal("100.00"),
        )
        self.stock_a = InventoryItem.objects.create(
            company=self.company_a,
            purchase_item=self.item_a,
            part=self.part,
            serial_number="TEN-A-001",
            barcode="TEN-A-001",
            status="IN_STOCK",
        )
        self.stock_b = InventoryItem.objects.create(
            company=self.company_b,
            purchase_item=self.item_b,
            part=self.part,
            serial_number="TEN-B-001",
            barcode="TEN-B-001",
            status="IN_STOCK",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin_a)

    def test_supplier_and_purchase_lists_hide_other_company(self):
        suppliers = self.client.get("/api/suppliers/")
        self.assertEqual(suppliers.status_code, 200)
        supplier_ids = {row["id"] for row in suppliers.data}
        self.assertIn(self.supplier_a.id, supplier_ids)
        self.assertNotIn(self.supplier_b.id, supplier_ids)

        purchases = self.client.get("/api/purchases/")
        self.assertEqual(purchases.status_code, 200)
        purchase_ids = {row["id"] for row in purchases.data}
        self.assertIn(self.purchase_a.id, purchase_ids)
        self.assertNotIn(self.purchase_b.id, purchase_ids)

    def test_purchase_create_rejects_other_company_supplier(self):
        response = self.client.post(
            "/api/purchases/",
            {
                "supplier": self.supplier_b.id,
                "invoice_number": "CROSS-TENANT",
                "invoice_date": "2026-09-29",
                "items": [{
                    "part": self.part.id,
                    "quantity": 1,
                    "purchase_price": "100.00",
                }],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Purchase.objects.filter(invoice_number="CROSS-TENANT").exists())

    def test_invoice_ocr_does_not_match_other_company_supplier(self):
        response = self.client.post(
            "/api/purchases/invoice-scan/analyze/",
            {
                "ocr_text": (
                    "Supplier B\nInvoice No: B-NEW-100\nDate: 29/09/2026\n"
                    "TEN-SED Tenant Sediment 1 100.00"
                )
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["draft"]["supplier"])

    def test_inventory_summary_counts_only_current_company_stock(self):
        response = self.client.get("/api/inventory/workflow/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["total_units"], 1)
        self.assertEqual(response.data["summary"]["in_stock"], 1)

    def test_receive_rejects_other_company_purchase_item(self):
        self.stock_b.status = "PENDING_RECEIPT"
        self.stock_b.save(update_fields=["status"])
        response = self.client.post(
            "/api/inventory/workflow/receive/",
            {"purchase_item_id": self.item_b.id, "code": "TEN-B-NEW"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.stock_b.refresh_from_db()
        self.assertEqual(self.stock_b.status, "PENDING_RECEIPT")
        self.assertEqual(self.stock_b.serial_number, "TEN-B-001")

    def test_issue_rejects_other_company_stock_id(self):
        response = self.client.post(
            "/api/inventory/issue/",
            {
                "engineer": self.engineer_a.id,
                "inventory_item": self.stock_b.id,
                "remarks": "must fail closed",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(EngineerBagItem.objects.filter(inventory_item=self.stock_b).exists())

    def test_part_request_create_stamps_engineer_company(self):
        engineer_client = APIClient()
        engineer_client.force_authenticate(self.engineer_a.user)
        response = engineer_client.post(
            "/api/inventory/part-requests/",
            {"part": self.part.id, "quantity": 1, "remarks": "Need one filter"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        row = PartRequest.objects.get(pk=response.data["id"])
        self.assertEqual(row.company_id, self.company_a.id)
        self.assertEqual(row.engineer_id, self.engineer_a.id)

    def test_part_request_same_action_id_is_created_once(self):
        engineer_client = APIClient()
        engineer_client.force_authenticate(self.engineer_a.user)
        payload = {"part": self.part.id, "quantity": 1, "remarks": "Retry-safe request"}
        first = engineer_client.post(
            "/api/inventory/part-requests/",
            payload,
            format="json",
            HTTP_X_ARI_ACTION_ID="part-request-retry-001",
        )
        second = engineer_client.post(
            "/api/inventory/part-requests/",
            payload,
            format="json",
            HTTP_X_ARI_ACTION_ID="part-request-retry-001",
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertFalse(first.data["idempotent_replay"])
        self.assertTrue(second.data["idempotent_replay"])
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(
            PartRequest.objects.filter(
                engineer=self.engineer_a,
                remarks="Retry-safe request",
            ).count(),
            1,
        )

    def test_my_bag_hides_mismatched_legacy_ownership(self):
        EngineerBagItem.objects.create(
            company=self.company_b,
            engineer=self.engineer_a,
            inventory_item=self.stock_b,
            status="ISSUED",
        )
        engineer_client = APIClient()
        engineer_client.force_authenticate(self.engineer_a.user)
        response = engineer_client.get("/api/inventory/my-bag/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])
