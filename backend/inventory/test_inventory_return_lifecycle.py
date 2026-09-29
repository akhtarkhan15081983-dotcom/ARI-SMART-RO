from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from employees.models import EmployeeProfile
from inventory.financials import inventory_financial_snapshot
from inventory.models import EngineerBagItem, InventoryAuditLog, InventoryItem
from partmaster.models import PartCategory, PartMaster
from purchase.models import Purchase, PurchaseItem, Supplier
from tenancy.models import Company, CompanyMembership


class InventoryReturnLifecycleTests(TransactionTestCase):
    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(
            name="Inventory Lifecycle Co",
            slug="inventory-lifecycle-co",
            phone="9000014001",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9899300001",
            password="Lifecycle@123",
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
        self.engineers = []
        for index in range(2):
            user = User.objects.create_user(
                phone=f"989930001{index}",
                password="Lifecycle@123",
                role="ENGINEER",
                is_verified=True,
                is_active=True,
            )
            CompanyMembership.objects.create(
                company=self.company,
                user=user,
                role="STAFF",
                is_active=True,
            )
            self.engineers.append(
                EmployeeProfile.objects.create(
                    company=self.company,
                    user=user,
                    employee_id=f"LIFE-ENG-{index + 1}",
                    gender="MALE",
                    joining_date=date(2026, 1, 1),
                    designation="ENGINEER",
                )
            )
        category = PartCategory.objects.create(name="Lifecycle Parts")
        self.part = PartMaster.objects.create(
            name="Lifecycle Membrane",
            code="LIFE-MEM",
            category=category,
            is_serialized=True,
        )
        supplier = Supplier.objects.create(company=self.company, name="Lifecycle Supplier")
        purchase = Purchase.objects.create(
            company=self.company,
            supplier=supplier,
            invoice_number="LIFE-001",
            invoice_date=date(2026, 9, 29),
        )
        self.purchase_item = PurchaseItem.objects.create(
            company=self.company,
            purchase=purchase,
            part=self.part,
            quantity=1,
            purchase_price=Decimal("350.00"),
        )
        self.stock = InventoryItem.objects.create(
            company=self.company,
            purchase_item=self.purchase_item,
            part=self.part,
            serial_number="LIFE-STOCK-001",
            barcode="LIFE-STOCK-001",
            status="IN_STOCK",
        )

    def _client(self):
        client = APIClient()
        client.force_authenticate(self.admin)
        return client

    def test_return_restores_stock_value_and_same_physical_unit_can_be_reissued(self):
        issued = self._client().post(
            "/api/inventory/issue/",
            {"engineer": self.engineers[0].id, "inventory_item": self.stock.id},
            format="json",
        )
        self.assertEqual(issued.status_code, 201)
        self.assertEqual(
            inventory_financial_snapshot(self.company.id)["warehouse_stock_value"],
            Decimal("0.00"),
        )

        returned = self._client().post(
            "/api/inventory/return/",
            {"inventory_item": self.stock.id, "remarks": "Unused part returned"},
            format="json",
        )
        self.assertEqual(returned.status_code, 200)
        self.stock.refresh_from_db()
        bag = EngineerBagItem.objects.get(inventory_item=self.stock)
        self.assertEqual(self.stock.status, "IN_STOCK")
        self.assertEqual(bag.status, "RETURNED")
        self.assertIsNotNone(bag.return_date)
        self.assertEqual(
            inventory_financial_snapshot(self.company.id)["warehouse_stock_value"],
            Decimal("350.00"),
        )
        self.assertTrue(
            InventoryAuditLog.objects.filter(
                inventory_item=self.stock,
                action="RETURNED",
                old_status="ISSUED",
                new_status="IN_STOCK",
            ).exists()
        )

        duplicate_return = self._client().post(
            "/api/inventory/return/",
            {"inventory_item": self.stock.id},
            format="json",
        )
        self.assertEqual(duplicate_return.status_code, 409)

        reissued = self._client().post(
            "/api/inventory/issue/",
            {"engineer": self.engineers[1].id, "inventory_item": self.stock.id},
            format="json",
        )
        self.assertEqual(reissued.status_code, 201)
        self.stock.refresh_from_db()
        bag.refresh_from_db()
        self.assertEqual(self.stock.status, "ISSUED")
        self.assertEqual(bag.status, "ISSUED")
        self.assertEqual(bag.engineer_id, self.engineers[1].id)
        self.assertIsNone(bag.return_date)
        self.assertEqual(EngineerBagItem.objects.filter(inventory_item=self.stock).count(), 1)

    def _parallel_issue(self, engineer_id):
        close_old_connections()
        try:
            response = self._client().post(
                "/api/inventory/issue/",
                {"engineer": engineer_id, "inventory_item": self.stock.id},
                format="json",
            )
            return response.status_code
        finally:
            close_old_connections()

    def test_two_simultaneous_engineer_issues_create_only_one_active_bag_assignment(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(self._parallel_issue, [row.id for row in self.engineers]))

        self.assertEqual(statuses.count(201), 1)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.status, "ISSUED")
        self.assertEqual(
            EngineerBagItem.objects.filter(
                inventory_item=self.stock,
                status="ISSUED",
            ).count(),
            1,
        )
