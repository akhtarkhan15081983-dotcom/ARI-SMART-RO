from datetime import date
from decimal import Decimal
from io import BytesIO
import json

import openpyxl
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from employees.models import EmployeeProfile
from inventory.models import (
    InventoryItem,
    EngineerBagItem,
    InventoryAuditLog,
    PartRequest,
)
from partmaster.models import PartCategory, PartMaster
from purchase.models import Supplier, Purchase, PurchaseItem


class InventoryWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            phone="9888800001", password="StrongPass@123", role="ADMIN", is_verified=True,
        )
        self.office = User.objects.create_user(
            phone="9888800002", password="StrongPass@123", role="OFFICE", is_verified=True,
        )
        engineer_user = User.objects.create_user(
            phone="9888800003", password="StrongPass@123", role="ENGINEER", is_verified=True,
        )
        self.engineer = EmployeeProfile.objects.create(
            user=engineer_user, gender="MALE", joining_date=date(2026, 1, 1),
            designation="ENGINEER", salary=Decimal("20000"),
        )
        category = PartCategory.objects.create(name="Workflow Parts")
        self.part = PartMaster.objects.create(
            name="RO Membrane", code="WF-MEM-01", category=category, is_serialized=True,
        )
        supplier = Supplier.objects.create(name="Workflow Supplier", gst_number="09ABCDE1234F1Z5")
        self.supplier = supplier
        purchase = Purchase.objects.create(
            supplier=supplier, invoice_number="WF-INV-1", invoice_date=date(2026, 9, 1),
        )
        self.purchase_item = PurchaseItem.objects.create(
            purchase=purchase, part=self.part, quantity=1, purchase_price=Decimal("1000"),
        )
        self.inventory_item = InventoryItem.objects.create(
            purchase_item=self.purchase_item, part=self.part,
        )
        self.part_request = PartRequest.objects.create(
            engineer=self.engineer, part=self.part, quantity=1, remarks="Required for service",
        )
        self.client = APIClient()

    def test_approval_receive_and_qr_fulfilment_are_atomic(self):
        self.client.force_authenticate(self.admin)
        approved = self.client.post(
            f"/api/inventory/workflow/requests/{self.part_request.id}/review/",
            {"action": "APPROVE", "remarks": "Approved for assigned work"}, format="json",
        )
        self.assertEqual(approved.status_code, 200)
        self.client.force_authenticate(self.office)
        received = self.client.post(
            "/api/inventory/workflow/receive/",
            {"purchase_item_id": self.purchase_item.id, "code": "QR-WF-0001"}, format="json",
        )
        self.assertEqual(received.status_code, 201)
        duplicate = self.client.post(
            "/api/inventory/workflow/receive/",
            {"purchase_item_id": self.purchase_item.id, "code": "QR-WF-0001"}, format="json",
        )
        self.assertEqual(duplicate.status_code, 409)
        fulfilled = self.client.post(
            f"/api/inventory/workflow/requests/{self.part_request.id}/fulfil/",
            {"codes": ["QR-WF-0001"]}, format="json",
        )
        self.assertEqual(fulfilled.status_code, 200)
        self.part_request.refresh_from_db()
        self.inventory_item.refresh_from_db()
        self.assertEqual(self.part_request.status, "FULFILLED")
        self.assertEqual(self.inventory_item.status, "ISSUED")
        self.assertTrue(EngineerBagItem.objects.filter(engineer=self.engineer, inventory_item=self.inventory_item).exists())

    def test_qr_labels_and_professional_inventory_report(self):
        self.client.force_authenticate(self.office)
        generated = self.client.post(
            "/api/inventory/workflow/generate-codes/",
            {"purchase_item_id": self.purchase_item.id}, format="json",
        )
        self.assertEqual(generated.status_code, 200)
        self.assertEqual(generated.data["generated"], 1)
        self.inventory_item.refresh_from_db()
        self.assertTrue(self.inventory_item.serial_number.startswith("ARI-WF-MEM-01-"))
        self.assertEqual(self.inventory_item.status, "PENDING_RECEIPT")

        labels = self.client.get(
            f"/api/inventory/workflow/qr-labels.pdf?purchase_item_id={self.purchase_item.id}"
        )
        self.assertEqual(labels.status_code, 200)
        self.assertEqual(labels["Content-Type"], "application/pdf")
        self.assertTrue(labels.content.startswith(b"%PDF"))

        report = self.client.get("/api/inventory/workflow/reports/inventory.xlsx")
        self.assertEqual(report.status_code, 200)
        workbook = openpyxl.load_workbook(BytesIO(report.content), read_only=True)
        self.assertEqual(
            workbook.sheetnames,
            ["Executive Summary", "Stock Ledger", "Purchases", "Part Requests", "Audit Trail"],
        )

    def test_invoice_ocr_preview_and_verified_purchase(self):
        self.client.force_authenticate(self.office)
        ocr_text = (
            "Workflow Supplier GST 09ABCDE1234F1Z5\n"
            "Invoice No: OCR-INV-100\nDate: 01/09/2026\n"
            "WF-MEM-01 RO Membrane 2 850.00"
        )
        preview = self.client.post(
            "/api/purchases/invoice-scan/analyze/",
            {"ocr_text": ocr_text}, format="multipart",
        )
        self.assertEqual(preview.status_code, 200)
        draft = preview.data["draft"]
        self.assertEqual(draft["supplier"], self.supplier.id)
        self.assertEqual(draft["invoice_number"], "OCR-INV-100")
        self.assertEqual(draft["items"][0]["part"], self.part.id)

        payload = {
            "supplier": self.supplier.id,
            "invoice_number": "OCR-INV-100",
            "invoice_date": "2026-09-01",
            "remarks": "Verified from invoice photo",
            "ocr_confidence": draft["confidence"],
            "items": [{"part": self.part.id, "quantity": 2, "purchase_price": "850.00"}],
        }
        confirmed = self.client.post(
            "/api/purchases/invoice-scan/confirm/",
            {
                "payload": json.dumps(payload),
                "ocr_text": ocr_text,
                "invoice_image": SimpleUploadedFile("invoice.jpg", b"invoice-image", content_type="image/jpeg"),
            }, format="multipart",
        )
        self.assertEqual(confirmed.status_code, 201)
        purchase = Purchase.objects.get(invoice_number="OCR-INV-100")
        self.assertEqual(purchase.entry_source, "INVOICE_OCR")
        self.assertEqual(purchase.verified_by, self.office)
        self.assertEqual(InventoryItem.objects.filter(purchase_item__purchase=purchase).count(), 2)

        duplicate = self.client.post(
            "/api/purchases/invoice-scan/confirm/",
            {"payload": json.dumps(payload), "ocr_text": ocr_text}, format="multipart",
        )
        self.assertEqual(duplicate.status_code, 409)


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
