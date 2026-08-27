from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from employees.models import EmployeeProfile
from inventory.models import (
    InventoryItem,
    EngineerBagItem,
    InventoryAuditLog,
)
from partmaster.models import PartCategory, PartMaster
from purchase.models import Supplier, Purchase, PurchaseItem


class InventorySecurityTests(TestCase):

    def setUp(self):

        User = get_user_model()

        # -----------------------------------------
        # USERS
        # -----------------------------------------

        self.engineer_user = User.objects.create_user(
            phone="9999900001",
            password="TestPassword123!",
        )

        self.other_user = User.objects.create_user(
            phone="9999900002",
            password="TestPassword123!",
        )

        self.staff_user = User.objects.create_user(
            phone="9999900003",
            password="TestPassword123!",
            role="OFFICE",
        )

        self.customer_user = User.objects.create_user(
            phone="9999900004",
            password="TestPassword123!",
            role="CUSTOMER",
            is_verified=True,
        )

        # -----------------------------------------
        # ENGINEERS
        # -----------------------------------------

        self.engineer = EmployeeProfile.objects.create(
            user=self.engineer_user,
            employee_id="TEST-001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )

        self.other_engineer = EmployeeProfile.objects.create(
            user=self.other_user,
            employee_id="TEST-002",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )

        # -----------------------------------------
        # API CLIENTS
        # -----------------------------------------

        self.client = APIClient()

        self.client.force_authenticate(
            user=self.engineer_user
        )

        self.other_client = APIClient()

        self.other_client.force_authenticate(
            user=self.other_user
        )

        self.staff_client = APIClient()
        self.staff_client.force_authenticate(user=self.staff_user)

        self.customer_client = APIClient()
        self.customer_client.force_authenticate(user=self.customer_user)

        # -----------------------------------------
        # PART CATEGORY
        # -----------------------------------------

        self.category = PartCategory.objects.create(
            name="Security Test Category",
        )

        # -----------------------------------------
        # PART
        # -----------------------------------------

        self.part = PartMaster.objects.create(
            name="Security Test Pump",
            code="TEST-PUMP-001",
            category=self.category,
            unit="PCS",
            is_serialized=True,
        )

        # -----------------------------------------
        # SUPPLIER
        # -----------------------------------------

        self.supplier = Supplier.objects.create(
            name="Security Test Supplier",
        )

        # -----------------------------------------
        # PURCHASE
        # -----------------------------------------

        self.purchase = Purchase.objects.create(
            supplier=self.supplier,
            invoice_number="TEST-INV-001",
            invoice_date=date(2026, 1, 1),
        )

        # -----------------------------------------
        # PURCHASE ITEM
        # -----------------------------------------

        self.purchase_item = PurchaseItem.objects.create(
            purchase=self.purchase,
            part=self.part,
            quantity=10,
            purchase_price=Decimal("100.00"),
        )

        # -----------------------------------------
        # INVENTORY ITEM
        # -----------------------------------------

        self.inventory_item = InventoryItem.objects.create(
            purchase_item=self.purchase_item,
            part=self.part,
            serial_number="TEST-SERIAL-001",
            status="IN_STOCK",
        )

    # =================================================
    # 1. WRONG ENGINEER CANNOT VERIFY ANOTHER ENGINEER
    # =================================================

    def test_wrong_engineer_cannot_verify_part(self):

        bag = EngineerBagItem.objects.create(
            engineer=self.engineer,
            inventory_item=self.inventory_item,
            status="ISSUED",
        )

        self.inventory_item.status = "ISSUED"
        self.inventory_item.save(
            update_fields=["status"]
        )

        response = self.other_client.post(
            "/api/inventory/verify/",
            {
                "engineer": self.engineer.id,
                "serial_number": "TEST-SERIAL-001",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertFalse(
            response.data["verified"]
        )

    # =================================================
    # 2. WRONG SERIAL MUST BE REJECTED
    # =================================================

    def test_wrong_serial_is_rejected(self):

        EngineerBagItem.objects.create(
            engineer=self.engineer,
            inventory_item=self.inventory_item,
            status="ISSUED",
        )

        self.inventory_item.status = "ISSUED"

        self.inventory_item.save(
            update_fields=["status"]
        )

        response = self.client.post(
            "/api/inventory/verify/",
            {
                "engineer": self.engineer.id,
                "serial_number": "WRONG-SERIAL",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertFalse(
            response.data["verified"]
        )

    # =================================================
    # 3. CORRECT ENGINEER + CORRECT SERIAL
    # =================================================

    def test_correct_engineer_can_verify_issued_part(self):

        EngineerBagItem.objects.create(
            engineer=self.engineer,
            inventory_item=self.inventory_item,
            status="ISSUED",
        )

        self.inventory_item.status = "ISSUED"

        self.inventory_item.save(
            update_fields=["status"]
        )

        response = self.client.post(
            "/api/inventory/verify/",
            {
                "engineer": self.engineer.id,
                "serial_number": "TEST-SERIAL-001",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["verified"]
        )

        self.assertEqual(
            response.data["serial_number"],
            "TEST-SERIAL-001",
        )

    # =================================================
    # 4. IN-STOCK ITEM CAN BE ISSUED
    # =================================================

    def test_stock_item_can_be_issued(self):

        response = self.staff_client.post(
            "/api/inventory/issue/",
            {
                "engineer": self.engineer.id,
                "inventory_item": self.inventory_item.id,
                "remarks": "Security test issue",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.inventory_item.refresh_from_db()

        self.assertEqual(
            self.inventory_item.status,
            "ISSUED",
        )

        self.assertTrue(
            EngineerBagItem.objects.filter(
                inventory_item=self.inventory_item,
                engineer=self.engineer,
                status="ISSUED",
            ).exists()
        )

    # =================================================
    # 5. AUDIT LOG CREATED ON SUCCESSFUL ISSUE
    # =================================================

    def test_successful_issue_creates_audit_log(self):

        response = self.staff_client.post(
            "/api/inventory/issue/",
            {
                "engineer": self.engineer.id,
                "inventory_item": self.inventory_item.id,
                "remarks": "Audit test",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        audit = InventoryAuditLog.objects.filter(
            inventory_item=self.inventory_item,
            action="ISSUED",
        ).first()

        self.assertIsNotNone(audit)

        self.assertEqual(
            audit.old_status,
            "IN_STOCK",
        )

        self.assertEqual(
            audit.new_status,
            "ISSUED",
        )

        self.assertEqual(
            audit.engineer,
            self.engineer,
        )

        self.assertEqual(
            audit.performed_by,
            self.staff_user,
        )

        self.assertEqual(
            audit.serial_number,
            "TEST-SERIAL-001",
        )

    # =================================================
    # 6. SAME PHYSICAL PART CANNOT BE ISSUED TWICE
    # =================================================

    def test_duplicate_issue_is_rejected(self):

        first_response = self.staff_client.post(
            "/api/inventory/issue/",
            {
                "engineer": self.engineer.id,
                "inventory_item": self.inventory_item.id,
            },
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            201,
        )

        second_response = self.staff_client.post(
            "/api/inventory/issue/",
            {
                "engineer": self.other_engineer.id,
                "inventory_item": self.inventory_item.id,
            },
            format="json",
        )

        self.assertEqual(
            second_response.status_code,
            400,
        )

        self.inventory_item.refresh_from_db()

        self.assertEqual(
            self.inventory_item.status,
            "ISSUED",
        )

        self.assertEqual(
            EngineerBagItem.objects.filter(
                inventory_item=self.inventory_item,
                status="ISSUED",
            ).count(),
            1,
        )

    # =================================================
    # 7. SECURITY REJECTION CREATES AUDIT LOG
    # =================================================

    def test_duplicate_issue_creates_security_audit(self):

        EngineerBagItem.objects.create(
            engineer=self.engineer,
            inventory_item=self.inventory_item,
            status="ISSUED",
        )

        self.inventory_item.status = "ISSUED"

        self.inventory_item.save(
            update_fields=["status"]
        )

        response = self.staff_client.post(
            "/api/inventory/issue/",
            {
                "engineer": self.other_engineer.id,
                "inventory_item": self.inventory_item.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertTrue(
            InventoryAuditLog.objects.filter(
                inventory_item=self.inventory_item,
                action="SECURITY_REJECT",
            ).exists()
        )

    def test_engineer_cannot_issue_stock_to_any_bag(self):
        response = self.client.post(
            "/api/inventory/issue/",
            {
                "engineer": self.engineer.id,
                "inventory_item": self.inventory_item.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.inventory_item.refresh_from_db()
        self.assertEqual(self.inventory_item.status, "IN_STOCK")

    def test_customer_cannot_issue_stock_to_any_bag(self):
        response = self.customer_client.post(
            "/api/inventory/issue/",
            {
                "engineer": self.engineer.id,
                "inventory_item": self.inventory_item.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.inventory_item.refresh_from_db()
        self.assertEqual(self.inventory_item.status, "IN_STOCK")

    # =================================================
    # 8. BAG MUST ONLY SHOW ISSUED ITEMS
    # =================================================

    def test_my_bag_only_returns_issued_items(self):

        bag = EngineerBagItem.objects.create(
            engineer=self.engineer,
            inventory_item=self.inventory_item,
            status="ISSUED",
        )

        self.inventory_item.status = "ISSUED"

        self.inventory_item.save(
            update_fields=["status"]
        )

        response = self.client.get(
            "/api/inventory/my-bag/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        self.assertEqual(
            response.data[0]["serial_number"],
            "TEST-SERIAL-001",
        )
