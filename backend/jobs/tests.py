from datetime import date
from decimal import Decimal
import threading
from datetime import timedelta
from django.db import close_old_connections
from django.conf import settings
from unittest import skipIf
from django.core.files.uploadedfile import SimpleUploadedFile

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from employees.models import EmployeeProfile
from customers.models import Customer
from products.models import ProductCategory, ROModel
from assets.models import ROAsset
from partmaster.models import PartCategory, PartMaster
from purchase.models import Supplier, Purchase, PurchaseItem

from inventory.models import (
    InventoryItem,
    EngineerBagItem,
    InventoryAuditLog,
)

from installation.models import Installation

from .models import (
    Job,
    JobMedia,
    JobPartUsed,
    JobSignature,
    JobActivityLog,
)
from django.utils import timezone
from .services import change_job_status


class JobPartSecurityFixtures:

    def setUp(self):

        User = get_user_model()

        # =====================================================
        # USERS
        # =====================================================

        self.engineer_user = User.objects.create_user(
            phone="8888800001",
            password="TestPassword123!",
        )

        self.other_user = User.objects.create_user(
            phone="8888800002",
            password="TestPassword123!",
        )

        # =====================================================
        # ENGINEERS
        # =====================================================

        self.engineer = EmployeeProfile.objects.create(
            user=self.engineer_user,
            employee_id="JOB-TEST-001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )

        self.other_engineer = EmployeeProfile.objects.create(
            user=self.other_user,
            employee_id="JOB-TEST-002",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )

        # =====================================================
        # CLIENTS
        # =====================================================

        self.client = APIClient()

        self.client.force_authenticate(
            user=self.engineer_user
        )

        self.other_client = APIClient()

        self.other_client.force_authenticate(
            user=self.other_user
        )

        # =====================================================
        # PRODUCT
        # =====================================================

        self.product_category = ProductCategory.objects.create(
            name="Job Security Test Category",
        )

        self.ro_model = ROModel.objects.create(
            category=self.product_category,
            model_name="Security Test RO",
            capacity="12 LPH",
            business_type="RENT",
            monthly_rent=Decimal("1000.00"),
            installation_charge=Decimal("500.00"),
            security_deposit=Decimal("1000.00"),
            selling_price=Decimal("10000.00"),
            warranty_months=12,
        )

        # =====================================================
        # CUSTOMER
        # =====================================================

        self.customer = Customer.objects.create(
            name="Job Security Customer",
            phone="7777700001",
            address="Security Test Address",
            city="Test City",
            state="Test State",
            pincode="123456",
            ro_model="Security Test RO",
            monthly_rent=Decimal("1000.00"),
        )

        # =====================================================
        # RO ASSET
        # =====================================================

        self.asset = ROAsset.objects.create(
            ro_model=self.ro_model,
            serial_number="TEST-ASSET-001",
            status="ASSIGNED",
            current_customer=self.customer,
        )

        # =====================================================
        # PART CATEGORY
        # =====================================================

        self.part_category = PartCategory.objects.create(
            name="Job Security Parts",
        )

        # =====================================================
        # PART MASTER
        # =====================================================

        self.part = PartMaster.objects.create(
            name="Job Security Pump",
            code="JOB-TEST-PUMP",
            category=self.part_category,
            unit="PCS",
            is_serialized=True,
        )

        # =====================================================
        # SUPPLIER
        # =====================================================

        self.supplier = Supplier.objects.create(
            name="Job Security Supplier",
        )

        # =====================================================
        # PURCHASE
        # =====================================================

        self.purchase = Purchase.objects.create(
            supplier=self.supplier,
            invoice_number="JOB-TEST-INV-001",
            invoice_date=date(2026, 1, 1),
        )

        # =====================================================
        # PURCHASE ITEM
        # =====================================================

        self.purchase_item = PurchaseItem.objects.create(
            purchase=self.purchase,
            part=self.part,
            quantity=10,
            purchase_price=Decimal("100.00"),
        )

        # =====================================================
        # INVENTORY ITEM
        # =====================================================

        self.inventory_item = InventoryItem.objects.create(
            purchase_item=self.purchase_item,
            part=self.part,
            serial_number="JOB-TEST-SERIAL-001",
            status="ISSUED",
        )

        # =====================================================
        # ENGINEER BAG
        # =====================================================

        self.bag_item = EngineerBagItem.objects.create(
            engineer=self.engineer,
            inventory_item=self.inventory_item,
            status="ISSUED",
        )

        # =====================================================
        # JOB
        # =====================================================

        self.job = Job.objects.create(
            customer=self.customer,
            ro_asset=self.asset,
            engineer=self.engineer,
            job_type="SERVICE",
            priority="MEDIUM",
            scheduled_date=timezone.now(),
            status="IN_PROGRESS",
        )

        # =====================================================
        # OTHER ENGINEER JOB
        # =====================================================

        self.other_job = Job.objects.create(
            customer=self.customer,
            ro_asset=self.asset,
            engineer=self.other_engineer,
            job_type="SERVICE",
            priority="MEDIUM",
            scheduled_date=timezone.now(),
            status="IN_PROGRESS",
        )

    # =========================================================
    # HELPER
    # =========================================================

    def parts_url(self, job):

        return reverse(
            "job-parts-used",
            kwargs={
                "pk": job.pk,
            },
        )


class JobPartSecurityTests(JobPartSecurityFixtures, TestCase):

    # =========================================================
    # 1. CORRECT ENGINEER CAN USE OWN BAG PART
    # =========================================================

    def test_correct_engineer_can_use_own_bag_part(self):

        response = self.client.post(
            self.parts_url(self.job),
            {
                "inventory_item": self.inventory_item.id,
                "quantity": 1,
                "remarks": "Security test installation",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertTrue(
            JobPartUsed.objects.filter(
                job=self.job,
                inventory_item=self.inventory_item,
            ).exists()
        )

        self.inventory_item.refresh_from_db()

        self.assertEqual(
            self.inventory_item.status,
            "INSTALLED",
        )

        self.bag_item.refresh_from_db()

        self.assertEqual(
            self.bag_item.status,
            "INSTALLED",
        )

    # =========================================================
    # 2. OTHER ENGINEER CANNOT USE THIS ENGINEER'S JOB
    # =========================================================

    def test_other_engineer_cannot_use_another_engineers_job(self):

        response = self.other_client.post(
            self.parts_url(self.job),
            {
                "inventory_item": self.inventory_item.id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertFalse(
            JobPartUsed.objects.filter(
                job=self.job,
                inventory_item=self.inventory_item,
            ).exists()
        )

        self.inventory_item.refresh_from_db()

        self.assertEqual(
            self.inventory_item.status,
            "ISSUED",
        )

    # =========================================================
    # 3. ENGINEER CANNOT USE PART FROM ANOTHER ENGINEER'S BAG
    # =========================================================

    def test_engineer_cannot_use_other_engineers_part(self):

        other_inventory = InventoryItem.objects.create(
            purchase_item=self.purchase_item,
            part=self.part,
            serial_number="JOB-TEST-SERIAL-002",
            status="ISSUED",
        )

        EngineerBagItem.objects.create(
            engineer=self.other_engineer,
            inventory_item=other_inventory,
            status="ISSUED",
        )

        response = self.client.post(
            self.parts_url(self.job),
            {
                "inventory_item": other_inventory.id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertFalse(
            JobPartUsed.objects.filter(
                job=self.job,
                inventory_item=other_inventory,
            ).exists()
        )

        other_inventory.refresh_from_db()

        self.assertEqual(
            other_inventory.status,
            "ISSUED",
        )

    # =========================================================
    # 4. IN-STOCK PART CANNOT BE USED DIRECTLY
    # =========================================================

    def test_in_stock_part_cannot_be_used(self):

        stock_item = InventoryItem.objects.create(
            purchase_item=self.purchase_item,
            part=self.part,
            serial_number="JOB-TEST-STOCK-001",
            status="IN_STOCK",
        )

        response = self.client.post(
            self.parts_url(self.job),
            {
                "inventory_item": stock_item.id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertFalse(
            JobPartUsed.objects.filter(
                job=self.job,
                inventory_item=stock_item,
            ).exists()
        )

        stock_item.refresh_from_db()

        self.assertEqual(
            stock_item.status,
            "IN_STOCK",
        )

    # =========================================================
    # 5. SERIALIZED PART CANNOT BE USED WITH QUANTITY > 1
    # =========================================================

    def test_serialized_part_quantity_cannot_exceed_one(self):

        response = self.client.post(
            self.parts_url(self.job),
            {
                "inventory_item": self.inventory_item.id,
                "quantity": 2,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertFalse(
            JobPartUsed.objects.filter(
                job=self.job,
                inventory_item=self.inventory_item,
            ).exists()
        )

        self.inventory_item.refresh_from_db()

        self.assertEqual(
            self.inventory_item.status,
            "ISSUED",
        )

    # =========================================================
    # 6. SAME PHYSICAL PART CANNOT BE USED TWICE
    # =========================================================

    def test_same_physical_part_cannot_be_used_twice(self):

        first_response = self.client.post(
            self.parts_url(self.job),
            {
                "inventory_item": self.inventory_item.id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            201,
        )

        second_response = self.client.post(
            self.parts_url(self.job),
            {
                "inventory_item": self.inventory_item.id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(
            second_response.status_code,
            400,
        )

        self.assertEqual(
            JobPartUsed.objects.filter(
                inventory_item=self.inventory_item,
            ).count(),
            1,
        )

    # =========================================================
    # 7. PART ALREADY USED BY ANOTHER JOB CANNOT BE REUSED
    # =========================================================

    def test_part_used_by_another_job_cannot_be_reused(self):

        JobPartUsed.objects.create(
            job=self.other_job,
            inventory_item=self.inventory_item,
            quantity=1,
        )

        self.inventory_item.status = "INSTALLED"

        self.inventory_item.save(
            update_fields=["status"]
        )

        self.bag_item.status = "INSTALLED"

        self.bag_item.save(
            update_fields=["status"]
        )

        response = self.client.post(
            self.parts_url(self.job),
            {
                "inventory_item": self.inventory_item.id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            JobPartUsed.objects.filter(
                inventory_item=self.inventory_item,
            ).count(),
            1,
        )

    # =========================================================
    # 8. SUCCESSFUL USE CREATES ACTIVITY LOG
    # =========================================================

    def test_successful_use_creates_activity_log(self):

        response = self.client.post(
            self.parts_url(self.job),
            {
                "inventory_item": self.inventory_item.id,
                "quantity": 1,
                "remarks": "Security audit test",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertTrue(
            JobActivityLog.objects.filter(
                job=self.job,
                engineer=self.engineer,
                activity="Part Installed",
            ).exists()
        )

    # =========================================================
    # 9. SUCCESSFUL USE CREATES INVENTORY AUDIT
    # =========================================================

    def test_successful_use_creates_inventory_audit(self):

        response = self.client.post(
            self.parts_url(self.job),
            {
                "inventory_item": self.inventory_item.id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        audit = InventoryAuditLog.objects.filter(
            inventory_item=self.inventory_item,
            job=self.job,
            action="INSTALLED",
        ).first()

        self.assertIsNotNone(
            audit
        )

        self.assertEqual(
            audit.engineer,
            self.engineer,
        )

        self.assertEqual(
            audit.performed_by,
            self.engineer_user,
        )

        self.assertEqual(
            audit.old_status,
            "ISSUED",
        )

        self.assertEqual(
            audit.new_status,
            "INSTALLED",
        )

    # =========================================================
    # 10. FAILED SECURITY ATTEMPT DOES NOT CHANGE INVENTORY
    # =========================================================

    def test_failed_security_attempt_does_not_change_inventory(self):

        response = self.other_client.post(
            self.parts_url(self.job),
            {
                "inventory_item": self.inventory_item.id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.inventory_item.refresh_from_db()

        self.assertEqual(
            self.inventory_item.status,
            "ISSUED",
        )

        self.bag_item.refresh_from_db()

        self.assertEqual(
            self.bag_item.status,
            "ISSUED",
        )

        self.assertFalse(
            JobPartUsed.objects.filter(
                job=self.job,
                inventory_item=self.inventory_item,
            ).exists()
        )

    # =========================================================
    # 12. JOB CANNOT COMPLETE WITHOUT PARTS
    # =========================================================

    def test_job_cannot_complete_without_parts(self):

        with self.assertRaisesMessage(
            ValueError,
            "Cannot complete job: parts have not been scanned.",
        ):
            change_job_status(
                self.job,
                "COMPLETED",
            )

        self.job.refresh_from_db()

        self.assertEqual(
            self.job.status,
            "IN_PROGRESS",
        )

    # =========================================================
    # 13. JOB CANNOT COMPLETE WITHOUT INSTALLATION
    # =========================================================

    def test_job_cannot_complete_without_installation(self):

        JobPartUsed.objects.create(
            job=self.job,
            inventory_item=self.inventory_item,
            quantity=1,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Cannot complete job: installation details are missing.",
        ):
            change_job_status(
                self.job,
                "COMPLETED",
            )

        self.job.refresh_from_db()

        self.assertEqual(
            self.job.status,
            "IN_PROGRESS",
        )

    # =========================================================
    # 14. JOB CANNOT COMPLETE WITHOUT AFTER PHOTO
    # =========================================================

    def test_job_cannot_complete_without_after_photo(self):

        JobPartUsed.objects.create(
            job=self.job,
            inventory_item=self.inventory_item,
            quantity=1,
        )

        Installation.objects.create(
            job=self.job,
            customer=self.customer,
            engineer=self.engineer,
            ro_asset=self.asset,
            business_type="RENT",
            scheduled_date=self.job.scheduled_date,
            status="IN_PROGRESS",
        )

        with self.assertRaisesMessage(
            ValueError,
            "Cannot complete job: after photo is missing.",
        ):
            change_job_status(
                self.job,
                "COMPLETED",
            )

        self.job.refresh_from_db()

        self.assertEqual(
            self.job.status,
            "IN_PROGRESS",
        )

    # =========================================================
    # 15. JOB CANNOT COMPLETE WITHOUT OTP
    # =========================================================

    def test_job_cannot_complete_without_otp(self):

        JobPartUsed.objects.create(
            job=self.job,
            inventory_item=self.inventory_item,
            quantity=1,
        )

        Installation.objects.create(
            job=self.job,
            customer=self.customer,
            engineer=self.engineer,
            ro_asset=self.asset,
            business_type="RENT",
            scheduled_date=self.job.scheduled_date,
            status="IN_PROGRESS",
        )

        JobMedia.objects.create(
            job=self.job,
            media_type="PHOTO",
            file=SimpleUploadedFile(
                "after.jpg",
                b"fake-image",
                content_type="image/jpeg",
            ),
            description="After Photo",
        )

        with self.assertRaisesMessage(
            ValueError,
            "Cannot complete job: customer OTP is not verified.",
        ):
            change_job_status(
                self.job,
                "COMPLETED",
            )

        self.job.refresh_from_db()

        self.assertEqual(
            self.job.status,
            "IN_PROGRESS",
        )

    # =========================================================
    # 16. JOB CANNOT COMPLETE WITHOUT SIGNATURE
    # =========================================================

    def test_job_cannot_complete_without_signature(self):

        JobPartUsed.objects.create(
            job=self.job,
            inventory_item=self.inventory_item,
            quantity=1,
        )

        Installation.objects.create(
            job=self.job,
            customer=self.customer,
            engineer=self.engineer,
            ro_asset=self.asset,
            business_type="RENT",
            scheduled_date=self.job.scheduled_date,
            status="IN_PROGRESS",
        )

        JobMedia.objects.create(
            job=self.job,
            media_type="PHOTO",
            file=SimpleUploadedFile(
                "after.jpg",
                b"fake-image",
                content_type="image/jpeg",
            ),
            description="After Photo",
        )

        self.job.otp_verified = True

        self.job.save(
            update_fields=["otp_verified"]
        )

        with self.assertRaisesMessage(
            ValueError,
            "Cannot complete job: customer signature is missing.",
        ):
            change_job_status(
                self.job,
                "COMPLETED",
            )

        self.job.refresh_from_db()

        self.assertEqual(
            self.job.status,
            "IN_PROGRESS",
        )

    # =========================================================
    # 17. JOB COMPLETES ONLY WHEN ALL REQUIREMENTS ARE MET
    # =========================================================

    def test_job_completes_only_when_all_requirements_are_met(self):

        # -----------------------------------------------------
        # 1. Part scanned
        # -----------------------------------------------------

        JobPartUsed.objects.create(
            job=self.job,
            inventory_item=self.inventory_item,
            quantity=1,
        )

        # -----------------------------------------------------
        # 2. Installation details
        # -----------------------------------------------------

        Installation.objects.create(
            job=self.job,
            customer=self.customer,
            engineer=self.engineer,
            ro_asset=self.asset,
            business_type="RENT",
            scheduled_date=self.job.scheduled_date,
            status="IN_PROGRESS",
        )

        # -----------------------------------------------------
        # 3. After Photo
        # -----------------------------------------------------

        JobMedia.objects.create(
            job=self.job,
            media_type="PHOTO",
            file=SimpleUploadedFile(
                "after.jpg",
                b"fake-image",
                content_type="image/jpeg",
            ),
            description="After Photo",
        )

        # -----------------------------------------------------
        # 4. Customer OTP verified
        # -----------------------------------------------------

        self.job.otp_verified = True

        self.job.save(
            update_fields=["otp_verified"]
        )

        # -----------------------------------------------------
        # 5. Customer Signature
        # -----------------------------------------------------

        JobSignature.objects.create(
            job=self.job,
            signature=SimpleUploadedFile(
                "signature.png",
                b"fake-signature",
                content_type="image/png",
            ),
            customer_name="Security Test Customer",
        )

        # -----------------------------------------------------
        # 6. Completion should now succeed
        # -----------------------------------------------------

        completed_job = change_job_status(
            self.job,
            "COMPLETED",
        )

        self.assertEqual(
            completed_job.status,
            "COMPLETED",
        )

        self.assertIsNotNone(
            completed_job.completed_at,
        )

        self.assertTrue(
            JobActivityLog.objects.filter(
                job=self.job,
                engineer=self.engineer,
                activity="Job Completed",
            ).exists()
        )

    # =========================================================
    # 18. INVALID COMPLETION STATUS TRANSITION
    # =========================================================

    def test_invalid_completion_status_transition_is_rejected(self):

        self.job.status = "ASSIGNED"
        self.job.save(
            update_fields=["status"]
        )

        with self.assertRaisesMessage(
            ValueError,
            "Cannot complete job: parts have not been scanned.",
        ):
            change_job_status(
                self.job,
                "COMPLETED",
            )

        self.job.refresh_from_db()

        self.assertEqual(
            self.job.status,
            "ASSIGNED",
        )
    def test_other_engineer_cannot_generate_otp_for_my_job(self):

        url = f"/api/jobs/{self.job.id}/generate-otp/"

        response = self.other_client.post(
            url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.job.refresh_from_db()

        self.assertIsNone(
            self.job.customer_otp,
        )


    def test_other_engineer_cannot_verify_otp_for_my_job(self):

        self.job.customer_otp = "123456"
        self.job.otp_verified = False

        self.job.save(
            update_fields=[
                "customer_otp",
                "otp_verified",
            ]
        )

        url = f"/api/jobs/{self.job.id}/verify-otp/"

        response = self.other_client.post(
            url,
            {
                "otp": "123456",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.job.refresh_from_db()

        self.assertFalse(
            self.job.otp_verified,
        )


    def test_other_engineer_cannot_upload_signature_for_my_job(self):

        url = f"/api/jobs/{self.job.id}/signature/"

        response = self.other_client.post(
            url,
            {
                "signature": SimpleUploadedFile(
                    "fraud.png",
                    b"fake-signature",
                    content_type="image/png",
                ),
                "customer_name": "Fake Customer",
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertFalse(
            JobSignature.objects.filter(
                job=self.job,
            ).exists()
        )

    def test_correct_engineer_can_verify_correct_otp(self):

        self.job.customer_otp = "123456"
        self.job.otp_verified = False
        self.job.otp_created_at = timezone.now()
        self.job.otp_attempts = 0

        self.job.save(
            update_fields=[
                "customer_otp",
                "otp_verified",
                "otp_created_at",
                "otp_attempts",
            ]
        )

        url = f"/api/jobs/{self.job.id}/verify-otp/"

        response = self.client.post(
            url,
            {
                "otp": "123456",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
            msg=getattr(response, "data", None),
        )

        self.job.refresh_from_db()

        self.assertTrue(
            self.job.otp_verified,
        )
    
    def test_expired_otp_is_rejected(self):

        self.job.customer_otp = "123456"
        self.job.otp_verified = False
        self.job.otp_created_at = (
            timezone.now() - timedelta(minutes=6)
        )
        self.job.otp_attempts = 0

        self.job.save(
            update_fields=[
                "customer_otp",
                "otp_verified",
                "otp_created_at",
                "otp_attempts",
            ]
        )

        url = f"/api/jobs/{self.job.id}/verify-otp/"

        response = self.client.post(
            url,
            {
                "otp": "123456",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
            msg=getattr(response, "data", None),
        )

        self.assertFalse(
            response.data["success"]
        )

        self.assertEqual(
            response.data["message"],
            "OTP has expired. Please generate a new OTP.",
        )

        self.job.refresh_from_db()

        self.assertIsNone(
            self.job.customer_otp
        )

        self.assertIsNone(
            self.job.otp_created_at
        )

        self.assertEqual(
            self.job.otp_attempts,
            0,
        )

    def test_otp_is_invalidated_after_max_failed_attempts(self):

        self.job.customer_otp = "123456"
        self.job.otp_verified = False
        self.job.otp_created_at = timezone.now()
        self.job.otp_attempts = 0

        self.job.save(
            update_fields=[
                "customer_otp",
                "otp_verified",
                "otp_created_at",
                "otp_attempts",
            ]
        )

        url = f"/api/jobs/{self.job.id}/verify-otp/"

        for attempt in range(5):

            response = self.client.post(
                url,
                {
                    "otp": "999999",
                },
                format="json",
            )

            self.assertEqual(
                response.status_code,
                400,
                msg=getattr(response, "data", None),
            )

        self.job.refresh_from_db()

        self.assertIsNone(
            self.job.customer_otp
        )

        self.assertIsNone(
            self.job.otp_created_at
        )

        self.assertEqual(
            self.job.otp_attempts,
            5,
        )

        self.assertFalse(
            self.job.otp_verified
        )

    def test_verified_otp_cannot_be_reused(self):

        self.job.customer_otp = "123456"
        self.job.otp_verified = False
        self.job.otp_created_at = timezone.now()
        self.job.otp_attempts = 0

        self.job.save(
            update_fields=[
                "customer_otp",
                "otp_verified",
                "otp_created_at",
                "otp_attempts",
            ]
        )

        url = f"/api/jobs/{self.job.id}/verify-otp/"

        # First verification
        response = self.client.post(
            url,
            {
                "otp": "123456",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
            msg=getattr(response, "data", None),
        )

        self.job.refresh_from_db()

        self.assertTrue(
            self.job.otp_verified
        )

        # Same OTP must not work again
        response = self.client.post(
            url,
            {
                "otp": "123456",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
            msg=getattr(response, "data", None),
        )

        self.assertFalse(
            response.data["success"]
        )

    def test_generate_otp_never_returns_otp(self):

        url = f"/api/jobs/{self.job.id}/generate-otp/"

        response = self.client.post(
            url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "otp",
            response.data,
        )

        self.assertTrue(
            response.data.get("success"),
        )

        self.assertEqual(
            response.data.get("message"),
            "Customer OTP generated successfully.",
        )

        self.job.refresh_from_db()

        self.assertIsNotNone(
            self.job.customer_otp,
        )

        self.assertEqual(
            len(self.job.customer_otp),
            6,
        )

        self.assertFalse(
            self.job.otp_verified,
        )

    def test_other_engineer_cannot_change_my_job_status(self):

        url = f"/api/jobs/{self.job.id}/change-status/"

        response = self.other_client.post(
            url,
            {
                "status": "ACCEPTED",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.job.refresh_from_db()

        self.assertEqual(
            self.job.status,
            "IN_PROGRESS",
        )


    def test_engineer_cannot_skip_job_status(self):

        self.job.status = "ASSIGNED"

        self.job.save(
            update_fields=["status"]
        )

        url = f"/api/jobs/{self.job.id}/change-status/"

        response = self.client.post(
            url,
            {
                "status": "ARRIVED",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.job.refresh_from_db()

        self.assertEqual(
            self.job.status,
            "ASSIGNED",
        )


    def test_engineer_cannot_move_completed_job_back(self):

        self.job.status = "COMPLETED"

        self.job.save(
            update_fields=["status"]
        )

        url = f"/api/jobs/{self.job.id}/change-status/"

        response = self.client.post(
            url,
            {
                "status": "ACCEPTED",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.job.refresh_from_db()

        self.assertEqual(
            self.job.status,
            "COMPLETED",
        )


    def test_engineer_can_follow_valid_status_sequence(self):

        self.job.status = "ASSIGNED"

        self.job.save(
            update_fields=["status"]
        )

        url = f"/api/jobs/{self.job.id}/change-status/"

        valid_sequence = [
            "ACCEPTED",
            "ON_THE_WAY",
            "ARRIVED",
            "IN_PROGRESS",
        ]

        for new_status in valid_sequence:

            response = self.client.post(
                url,
                {
                    "status": new_status,
                },
                format="json",
            )

            self.assertEqual(
                response.status_code,
                200,
                msg=(
                    f"Expected 200 for "
                    f"status {new_status}, "
                    f"got {response.status_code}: "
                    f"{getattr(response, 'data', None)}"
                ),
            )

            self.job.refresh_from_db()

            self.assertEqual(
                self.job.status,
                new_status,
            )

    def test_other_engineer_cannot_upload_media_to_my_job(self):

        url = f"/api/jobs/{self.job.id}/media/"

        response = self.other_client.post(
            url,
            {
                "media_type": "PHOTO",
                "file": SimpleUploadedFile(
                    "fraud.jpg",
                    b"fake-photo",
                    content_type="image/jpeg",
                ),
                "description": "Fraud attempt",
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertFalse(
            JobMedia.objects.filter(
                job=self.job,
            ).exists()
        )


    def test_correct_engineer_can_upload_media_to_own_job(self):

        url = f"/api/jobs/{self.job.id}/media/"

        response = self.client.post(
            url,
            {
                "media_type": "PHOTO",
                "file": SimpleUploadedFile(
                    "after.jpg",
                    b"fake-photo",
                    content_type="image/jpeg",
                ),
                "description": "After Photo",
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertTrue(
            JobMedia.objects.filter(
                job=self.job,
                media_type="PHOTO",
                description="After Photo",
            ).exists()
        )


    def test_other_engineer_cannot_upload_gps_to_my_job(self):

        url = f"/api/jobs/{self.job.id}/gps/"

        response = self.other_client.post(
            url,
            {
                "latitude": "28.6139390",
                "longitude": "77.2090210",
                "accuracy": "5.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertEqual(
            self.job.gps_logs.count(),
            0,
        )


    def test_correct_engineer_can_upload_gps_to_own_job(self):

        url = f"/api/jobs/{self.job.id}/gps/"

        response = self.client.post(
            url,
            {
                "latitude": "28.6139390",
                "longitude": "77.2090210",
                "accuracy": "5.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        gps = self.job.gps_logs.first()

        self.assertIsNotNone(
            gps,
        )

        self.assertEqual(
            gps.latitude,
            Decimal("28.6139390"),
        )

        self.assertEqual(
            gps.longitude,
            Decimal("77.2090210"),
        )

    def test_other_engineer_cannot_view_my_job_detail(self):

        url = f"/api/jobs/{self.job.id}/"

        response = self.other_client.get(url)

        self.assertEqual(
            response.status_code,
            404,
        )


    def test_my_jobs_does_not_expose_other_engineers_jobs(self):

        url = "/api/jobs/my-jobs/"

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            200,
        )

        job_ids = [
            item["id"]
            for item in response.data
        ]

        self.assertIn(
            self.job.id,
            job_ids,
        )

        if hasattr(self, "other_job"):
            self.assertNotIn(
                self.other_job.id,
                job_ids,
            )


    def test_viewset_does_not_expose_other_engineers_job(self):

        url = f"/api/jobs/{self.job.id}/"

        response = self.other_client.get(url)

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_other_engineer_cannot_search_my_job(self):

        url = "/api/jobs/search/"

        response = self.other_client.get(
            url,
            {
                "q": self.job.job_id,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        returned_ids = [
            item["id"]
            for item in response.data
        ]

        self.assertNotIn(
            self.job.id,
            returned_ids,
        )


    def test_engineer_can_search_own_job(self):

        url = "/api/jobs/search/"

        response = self.client.get(
            url,
            {
                "q": self.job.job_id,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        returned_ids = [
            item["id"]
            for item in response.data
        ]

        self.assertIn(
            self.job.id,
            returned_ids,
        )

    def test_other_engineer_cannot_accept_my_job(self):

        self.job.status = "ASSIGNED"
        self.job.save(update_fields=["status"])

        url = f"/api/jobs/{self.job.id}/accept/"

        response = self.other_client.post(
            url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.job.refresh_from_db()

        self.assertEqual(
            self.job.status,
            "ASSIGNED",
        )

        self.assertIsNone(
            self.job.accepted_at,
        )


    def test_correct_engineer_can_accept_assigned_job(self):

        # This test is specifically for accepting
        # an ASSIGNED job.

        self.job.status = "ASSIGNED"
        self.job.accepted_at = None

        self.job.save(
            update_fields=[
                "status",
                "accepted_at",
            ]
        )

        url = f"/api/jobs/{self.job.id}/accept/"

        response = self.client.post(
            url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
            msg=getattr(response, "data", None),
        )

        self.job.refresh_from_db()

        self.assertEqual(
            self.job.status,
            "ACCEPTED",
        )

        self.assertIsNotNone(
            self.job.accepted_at,
        )


    def test_accepting_job_creates_activity_log(self):

        self.job.status = "ASSIGNED"
        self.job.accepted_at = None

        self.job.save(
            update_fields=[
                "status",
                "accepted_at",
            ]
        )

        JobActivityLog.objects.filter(
            job=self.job,
            activity="Job Accepted",
        ).delete()

        url = f"/api/jobs/{self.job.id}/accept/"

        response = self.client.post(
            url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            JobActivityLog.objects.filter(
                job=self.job,
                engineer=self.job.engineer,
                activity="Job Accepted",
            ).exists()
        )


    def test_cannot_accept_already_accepted_job(self):

        self.job.status = "ACCEPTED"

        self.job.save(
            update_fields=["status"]
        )

        url = f"/api/jobs/{self.job.id}/accept/"

        response = self.client.post(
            url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.job.refresh_from_db()

        self.assertEqual(
            self.job.status,
            "ACCEPTED",
        )

    def test_unauthenticated_user_cannot_access_job_apis(self):

        client = APIClient()

        endpoints = [
            (
                "GET",
                f"/api/jobs/{self.job.id}/",
                None,
            ),
            (
                "GET",
                "/api/jobs/my-jobs/",
                None,
            ),
            (
                "GET",
                "/api/jobs/search/?q=JOB",
                None,
            ),
            (
                "POST",
                f"/api/jobs/{self.job.id}/accept/",
                {},
            ),
            (
                "POST",
                f"/api/jobs/{self.job.id}/change-status/",
                {
                    "status": "ACCEPTED",
                },
            ),
            (
                "POST",
                f"/api/jobs/{self.job.id}/gps/",
                {
                    "latitude": "28.6139390",
                    "longitude": "77.2090210",
                    "accuracy": "5.00",
                },
            ),
            (
                "POST",
                f"/api/jobs/{self.job.id}/generate-otp/",
                {},
            ),
            (
                "POST",
                f"/api/jobs/{self.job.id}/verify-otp/",
                {
                    "otp": "123456",
                },
            ),
        ]

        for method, url, data in endpoints:

            if method == "GET":
                response = client.get(url)
            else:
                response = client.post(
                    url,
                    data or {},
                    format="json",
                )

            self.assertEqual(
                response.status_code,
                401,
                msg=(
                    f"{method} {url} returned "
                    f"{response.status_code} instead of 401. "
                    f"Response: {getattr(response, 'data', None)}"
                ),
            )

    def test_successful_part_install_updates_inventory_and_bag(self):

        self.job.status = "IN_PROGRESS"
        self.job.save(
            update_fields=["status"]
        )

        inventory_item = self.inventory_item

        bag_item = EngineerBagItem.objects.get(
            inventory_item=inventory_item,
            engineer=self.engineer,
            status="ISSUED",
        )

        url = f"/api/jobs/{self.job.id}/parts/"

        response = self.client.post(
            url,
            {
                "inventory_item": inventory_item.id,
                "quantity": 1,
                "remarks": "Installed during job",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        inventory_item.refresh_from_db()
        bag_item.refresh_from_db()

        self.assertEqual(
            inventory_item.status,
            "INSTALLED",
        )

        self.assertEqual(
            bag_item.status,
            "INSTALLED",
        )

        self.assertIsNotNone(
            bag_item.install_date,
        )

        self.assertTrue(
            JobPartUsed.objects.filter(
                job=self.job,
                inventory_item=inventory_item,
                quantity=1,
            ).exists()
        )

        self.assertTrue(
            InventoryAuditLog.objects.filter(
                inventory_item=inventory_item,
                job=self.job,
                action="INSTALLED",
                old_status="ISSUED",
                new_status="INSTALLED",
            ).exists()
        )

        self.assertTrue(
            JobActivityLog.objects.filter(
                job=self.job,
                engineer=self.engineer,
                activity="Part Installed",
            ).exists()
        )

    def test_search_does_not_expose_other_engineers_job(self):

        url = "/api/jobs/search/?q=" + self.job.job_id

        response = self.other_client.get(url)

        self.assertEqual(
            response.status_code,
            200,
        )

        results = response.data

        if isinstance(results, dict):
            results = results.get(
                "results",
                []
            )

        returned_job_ids = [
            item["job_id"]
            for item in results
        ]

        self.assertNotIn(
            self.job.job_id,
            returned_job_ids,
        )


class JobPartConcurrencyTests(
    JobPartSecurityFixtures,
    TransactionTestCase,
):

    @skipIf(
        settings.DATABASES["default"]["ENGINE"]
        == "django.db.backends.sqlite3",
        "SQLite does not support this concurrency test reliably.",
    )
    def test_concurrent_install_same_part_only_one_succeeds(self):

        results = []

        def install_part():

            close_old_connections()

            client = APIClient()

            client.force_authenticate(
                user=self.engineer_user
            )

            response = client.post(
                self.parts_url(self.job),
                {
                    "inventory_item": self.inventory_item.id,
                    "quantity": 1,
                    "remarks": "Concurrency security test",
                },
                format="json",
            )

            results.append(
                response.status_code
            )

            close_old_connections()

        thread1 = threading.Thread(
            target=install_part
        )

        thread2 = threading.Thread(
            target=install_part
        )

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        self.assertEqual(
            len(results),
            2,
        )

        # Exactly one request must succeed.
        self.assertEqual(
            results.count(201),
            1,
        )

        # The second request must be rejected.
        self.assertEqual(
            results.count(400),
            1,
        )

        # Only one physical usage record may exist.
        self.assertEqual(
            JobPartUsed.objects.filter(
                inventory_item=self.inventory_item,
            ).count(),
            1,
        )

        self.inventory_item.refresh_from_db()

        self.assertEqual(
            self.inventory_item.status,
            "INSTALLED",
        )

        self.bag_item.refresh_from_db()

        self.assertEqual(
            self.bag_item.status,
            "INSTALLED",
        )
