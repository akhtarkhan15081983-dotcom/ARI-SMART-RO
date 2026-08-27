from django.test import TestCase

from rest_framework.test import APIClient

from accounts.models import User

from .models import Customer
from products.models import ROModel, ProductCategory
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient

from accounts.models import User
from customers.models import Customer
from employees.models import EmployeeProfile

from products.models import (
    ROModel,
    ProductCategory,
)

from assets.models.asset import ROAsset

from jobs.models import (
    Job,
    JobPartUsed,
)

from inventory.models import InventoryItem

from purchase.models import (
    Supplier,
    Purchase,
    PurchaseItem,
)

from partmaster.models import (
    PartCategory,
    PartMaster,
)
from referrals.models import (
    WalletReward,
    WalletLedgerEntry,
)

class CustomerProfileTests(TestCase):

    def setUp(self):

        self.client = APIClient()

        # ----------------------------------------------------
        # VERIFIED CUSTOMER
        # ----------------------------------------------------

        self.user = User.objects.create_user(
            phone="9000000101",
            password="Test@123",
            first_name="Test",
            last_name="Customer",
            role="CUSTOMER",
            is_verified=True,
        )

        # ----------------------------------------------------
        # SECOND CUSTOMER
        # ----------------------------------------------------

        self.other_user = User.objects.create_user(
            phone="9000000102",
            password="Test@123",
            first_name="Other",
            last_name="Customer",
            role="CUSTOMER",
            is_verified=True,
        )

        self.client.force_authenticate(
            user=self.user
        )

    # ========================================================
    # 1. VERIFIED CUSTOMER CAN CREATE PROFILE
    # ========================================================

    def test_verified_customer_can_create_profile(self):

        response = self.client.post(
            "/api/customers/profile/",
            {
                "name": "Test Customer",
                "alternate_phone": "",
                "email": "test@example.com",
                "gender": "MALE",
                "address": "Test Address",
                "area": "Test Area",
                "city": "Delhi",
                "state": "Delhi",
                "pincode": "110001",
                "ro_model": "Test RO",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        customer = Customer.objects.get(
            user=self.user
        )

        self.assertEqual(
            customer.phone,
            self.user.phone,
        )

        self.assertEqual(
            customer.name,
            "Test Customer",
        )

        self.assertIsNotNone(
            customer.customer_id
        )

        self.assertIsNotNone(
            customer.card_number
        )

    # ========================================================
    # 2. UNVERIFIED CUSTOMER CANNOT CREATE PROFILE
    # ========================================================

    def test_unverified_customer_cannot_create_profile(self):

        self.user.is_verified = False

        self.user.save(
            update_fields=[
                "is_verified"
            ]
        )

        response = self.client.post(
            "/api/customers/profile/",
            {
                "name": "Blocked Customer",
                "address": "Test Address",
                "city": "Delhi",
                "state": "Delhi",
                "pincode": "110001",
                "ro_model": "Test RO",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertFalse(
            Customer.objects.filter(
                user=self.user
            ).exists()
        )

    def test_unverified_customer_cannot_read_phone_matched_records(self):
        customer = Customer.objects.create(
            name="Protected Customer",
            phone=self.user.phone,
            address="Private Address",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            ro_model="Test RO",
        )
        self.user.is_verified = False
        self.user.save(update_fields=["is_verified"])

        responses = [
            self.client.get("/api/customers/"),
            self.client.get(f"/api/customers/{customer.id}/"),
            self.client.get("/api/customers/search/?q=Protected"),
            self.client.get("/api/customers/rent/"),
        ]

        for response in responses:
            self.assertEqual(response.status_code, 403)

    # ========================================================
    # 3. CUSTOMER CAN READ OWN PROFILE
    # ========================================================

    def test_customer_can_read_own_profile(self):

        customer = Customer.objects.create(
            user=self.user,
            name="Test Customer",
            phone=self.user.phone,
            address="Test Address",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            ro_model="Test RO",
        )

        response = self.client.get(
            "/api/customers/profile/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["success"]
        )

        self.assertEqual(
            response.data["profile"]["id"],
            customer.id,
        )

        self.assertEqual(
            response.data["profile"]["name"],
            "Test Customer",
        )

    # ========================================================
    # 4. CUSTOMER CAN UPDATE OWN PROFILE
    # ========================================================

    def test_customer_can_update_own_profile(self):

        Customer.objects.create(
            user=self.user,
            name="Old Name",
            phone=self.user.phone,
            address="Old Address",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            ro_model="Test RO",
        )

        response = self.client.patch(
            "/api/customers/profile/",
            {
                "name": "New Name",
                "address": "New Address",
                "area": "New Area",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        customer = Customer.objects.get(
            user=self.user
        )

        self.assertEqual(
            customer.name,
            "New Name",
        )

        self.assertEqual(
            customer.address,
            "New Address",
        )

        self.assertEqual(
            customer.area,
            "New Area",
        )

    # ========================================================
    # 5. CUSTOMER CANNOT ACCESS ANOTHER CUSTOMER PROFILE
    # ========================================================

    def test_customer_cannot_access_another_profile(self):

        Customer.objects.create(
            user=self.other_user,
            name="Other Customer",
            phone=self.other_user.phone,
            address="Other Address",
            city="Delhi",
            state="Delhi",
            pincode="110002",
            ro_model="Other RO",
        )

        response = self.client.get(
            "/api/customers/profile/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertFalse(
            response.data["profile_exists"]
        )

    # ========================================================
    # 6. LEGACY CUSTOMER IS LINKED BY PHONE
    # ========================================================

    def test_legacy_customer_is_linked_by_phone(self):

        legacy_customer = Customer.objects.create(
            user=None,
            name="Legacy Customer",
            phone=self.user.phone,
            address="Legacy Address",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            ro_model="Legacy RO",
        )

        response = self.client.get(
            "/api/customers/profile/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        legacy_customer.refresh_from_db()

        self.assertEqual(
            legacy_customer.user_id,
            self.user.id,
        )

        self.assertEqual(
            response.data["profile"]["id"],
            legacy_customer.id,
        )

    # ========================================================
    # 7. CUSTOMER CANNOT CHANGE PHONE
    # ========================================================

    def test_customer_cannot_change_phone(self):

        Customer.objects.create(
            user=self.user,
            name="Test Customer",
            phone=self.user.phone,
            address="Test Address",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            ro_model="Test RO",
        )

        response = self.client.patch(
            "/api/customers/profile/",
            {
                "phone": "9111111111",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        customer = Customer.objects.get(
            user=self.user
        )

        self.assertEqual(
            customer.phone,
            self.user.phone,
        )

    # ========================================================
    # 8. CUSTOMER CANNOT CHANGE RENT
    # ========================================================

    def test_customer_cannot_change_rent(self):

        Customer.objects.create(
            user=self.user,
            name="Test Customer",
            phone=self.user.phone,
            address="Test Address",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            ro_model="Test RO",
            monthly_rent=500,
        )

        response = self.client.patch(
            "/api/customers/profile/",
            {
                "monthly_rent": "1",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        customer = Customer.objects.get(
            user=self.user
        )

        self.assertEqual(
            customer.monthly_rent,
            500,
        )

    # ========================================================
    # 9. CUSTOMER CANNOT CHANGE SECURITY DEPOSIT
    # ========================================================

    def test_customer_cannot_change_security_deposit(
        self
    ):

        Customer.objects.create(
            user=self.user,
            name="Test Customer",
            phone=self.user.phone,
            address="Test Address",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            ro_model="Test RO",
            security_deposit=2000,
        )

        response = self.client.patch(
            "/api/customers/profile/",
            {
                "security_deposit": "1",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        customer = Customer.objects.get(
            user=self.user
        )

        self.assertEqual(
            customer.security_deposit,
            2000,
        )

    # ========================================================
    # 10. CUSTOMER CANNOT CHANGE ENGINEER
    # ========================================================

    def test_customer_cannot_change_engineer(self):

        customer = Customer.objects.create(
            user=self.user,
            name="Test Customer",
            phone=self.user.phone,
            address="Test Address",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            ro_model="Test RO",
        )

        response = self.client.patch(
            "/api/customers/profile/",
            {
                "assigned_engineer": 99999,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        customer.refresh_from_db()

        self.assertIsNone(
            customer.assigned_engineer
        )
    # ========================================================
    # WELCOME REWARD
    # ========================================================

    def test_customer_profile_creation_creates_welcome_reward(self):

        response = self.client.post(
            "/api/customers/profile/",
            {
                "name": "Welcome Customer",
                "alternate_phone": "",
                "email": "welcome@example.com",
                "gender": "MALE",
                "address": "Test Address",
                "area": "Test Area",
                "city": "Delhi",
                "state": "Delhi",
                "pincode": "110001",
                "ro_model": "Test RO",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        reward = WalletReward.objects.get(
            owner=self.user,
            reward_type="APP_WELCOME",
        )

        self.assertEqual(
            reward.total_amount,
            Decimal("50.00"),
        )

        self.assertEqual(
            reward.remaining_amount,
            Decimal("50.00"),
        )

        self.assertEqual(
            reward.max_bill_percent,
            Decimal("40.00"),
        )

        self.assertEqual(
            reward.usage_categories,
            [
                "PURCHASE",
                "PARTS",
                "SERVICE",
            ],
        )

        self.assertEqual(
            WalletLedgerEntry.objects.filter(
                user=self.user,
                reward=reward,
                entry_type="CREDIT",
            ).count(),
            1,
        )


    def test_welcome_reward_expires_in_90_days(self):

        self.client.post(
            "/api/customers/profile/",
            {
                "name": "Expiry Customer",
                "alternate_phone": "",
                "email": "expiry@example.com",
                "gender": "MALE",
                "address": "Test Address",
                "area": "Test Area",
                "city": "Delhi",
                "state": "Delhi",
                "pincode": "110001",
                "ro_model": "Test RO",
            },
            format="json",
        )

        reward = WalletReward.objects.get(
            owner=self.user,
            reward_type="APP_WELCOME",
        )

        expected_expiry = reward.activated_at + timedelta(
            days=90
        )

        self.assertAlmostEqual(
            reward.expires_at.timestamp(),
            expected_expiry.timestamp(),
            delta=1,
        )


    def test_welcome_reward_is_not_created_twice(self):

        response = self.client.post(
            "/api/customers/profile/",
            {
                "name": "Duplicate Customer",
                "alternate_phone": "",
                "email": "duplicate@example.com",
                "gender": "MALE",
                "address": "Test Address",
                "area": "Test Area",
                "city": "Delhi",
                "state": "Delhi",
                "pincode": "110001",
                "ro_model": "Test RO",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            WalletReward.objects.filter(
                owner=self.user,
                reward_type="APP_WELCOME",
            ).count(),
            1,
        )

        response = self.client.post(
            "/api/customers/profile/",
            {
                "name": "Duplicate Customer Again",
                "alternate_phone": "",
                "email": "duplicate2@example.com",
                "gender": "MALE",
                "address": "Test Address",
                "area": "Test Area",
                "city": "Delhi",
                "state": "Delhi",
                "pincode": "110001",
                "ro_model": "Test RO",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            WalletReward.objects.filter(
                owner=self.user,
                reward_type="APP_WELCOME",
            ).count(),
            1,
        )


    def test_unverified_customer_gets_no_welcome_reward(self):

        self.user.is_verified = False

        self.user.save(
            update_fields=[
                "is_verified"
            ]
        )

        response = self.client.post(
            "/api/customers/profile/",
            {
                "name": "Unverified Customer",
                "alternate_phone": "",
                "email": "unverified@example.com",
                "gender": "MALE",
                "address": "Test Address",
                "area": "Test Area",
                "city": "Delhi",
                "state": "Delhi",
                "pincode": "110001",
                "ro_model": "Test RO",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertFalse(
            WalletReward.objects.filter(
                owner=self.user,
                reward_type="APP_WELCOME",
            ).exists()
        )    
# ============================================================
# CUSTOMER APP - MY RO TESTS
# ============================================================

from assets.models.asset import ROAsset
from products.models import ROModel


class MyROTests(TestCase):

    def setUp(self):

        self.client = APIClient()

        # ----------------------------------------------------
        # VERIFIED CUSTOMER
        # ----------------------------------------------------

        self.user = User.objects.create_user(
            phone="9000000201",
            password="Test@123",
            first_name="RO",
            last_name="Customer",
            role="CUSTOMER",
            is_verified=True,
        )

        self.customer = Customer.objects.create(
            user=self.user,
            name="RO Customer",
            phone=self.user.phone,
            address="Test Address",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            ro_model="Test RO",
        )

        # ----------------------------------------------------
        # SECOND CUSTOMER
        # ----------------------------------------------------

        self.other_user = User.objects.create_user(
            phone="9000000202",
            password="Test@123",
            first_name="Other",
            last_name="Customer",
            role="CUSTOMER",
            is_verified=True,
        )

        self.other_customer = Customer.objects.create(
            user=self.other_user,
            name="Other Customer",
            phone=self.other_user.phone,
            address="Other Address",
            city="Delhi",
            state="Delhi",
            pincode="110002",
            ro_model="Other RO",
        )

        # ----------------------------------------------------
        # RO MODEL
        # ----------------------------------------------------

        self.ro_category = ProductCategory.objects.create(
            name="Test Category",
            description="Test category for My RO tests",
            is_active=True,
        )

        self.ro_model = ROModel.objects.create(
            category=self.ro_category,
            model_name="Test RO Model",
            capacity="25 LPH",
            business_type="SALE",
            monthly_rent=0,
            installation_charge=0,
            security_deposit=0,
            selling_price=10000,
            warranty_months=12,
            is_active=True,
        )

        # ----------------------------------------------------
        # AUTHENTICATE
        # ----------------------------------------------------

        self.client.force_authenticate(
            user=self.user
        )

    # ========================================================
    # CUSTOMER CAN SEE OWN RO
    # ========================================================

    def test_customer_can_see_own_ro(self):

        asset = ROAsset.objects.create(
            ro_model=self.ro_model,
            serial_number="TEST-SERIAL-001",
            qr_code="QR-001",
            status="INSTALLED",
            current_customer=self.customer,
            is_active=True,
        )

        response = self.client.get(
            "/api/customers/my-ro/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["success"]
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

        self.assertEqual(
            response.data["ros"][0]["id"],
            asset.id,
        )

        self.assertEqual(
            response.data["ros"][0][
                "serial_number"
            ],
            "TEST-SERIAL-001",
        )

    # ========================================================
    # CUSTOMER CANNOT SEE OTHER CUSTOMER RO
    # ========================================================

    def test_customer_cannot_see_other_customer_ro(
        self
    ):

        ROAsset.objects.create(
            ro_model=self.ro_model,
            serial_number="OTHER-SERIAL-001",
            qr_code="OTHER-QR-001",
            status="INSTALLED",
            current_customer=self.other_customer,
            is_active=True,
        )

        response = self.client.get(
            "/api/customers/my-ro/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            0,
        )

    # ========================================================
    # INACTIVE RO IS NOT SHOWN
    # ========================================================

    def test_inactive_ro_is_not_shown(self):

        ROAsset.objects.create(
            ro_model=self.ro_model,
            serial_number="INACTIVE-SERIAL",
            qr_code="INACTIVE-QR",
            status="INSTALLED",
            current_customer=self.customer,
            is_active=False,
        )

        response = self.client.get(
            "/api/customers/my-ro/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            0,
        )

    # ========================================================
    # RETURNED RO IS NOT SHOWN
    # ========================================================

    def test_returned_ro_is_not_shown(self):

        ROAsset.objects.create(
            ro_model=self.ro_model,
            serial_number="RETURNED-SERIAL",
            qr_code="RETURNED-QR",
            status="RETURNED",
            current_customer=self.customer,
            is_active=True,
        )

        response = self.client.get(
            "/api/customers/my-ro/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            0,
        )

    # ========================================================
    # SCRAPPED RO IS NOT SHOWN
    # ========================================================

    def test_scrapped_ro_is_not_shown(self):

        ROAsset.objects.create(
            ro_model=self.ro_model,
            serial_number="SCRAP-SERIAL",
            qr_code="SCRAP-QR",
            status="SCRAP",
            current_customer=self.customer,
            is_active=True,
        )

        response = self.client.get(
            "/api/customers/my-ro/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            0,
        )

    # ========================================================
    # CUSTOMER CAN HAVE MULTIPLE ACTIVE ROS
    # ========================================================

    def test_customer_can_have_multiple_active_ros(
        self
    ):

        ROAsset.objects.create(
            ro_model=self.ro_model,
            serial_number="MULTI-SERIAL-001",
            qr_code="MULTI-QR-001",
            status="INSTALLED",
            current_customer=self.customer,
            is_active=True,
        )

        ROAsset.objects.create(
            ro_model=self.ro_model,
            serial_number="MULTI-SERIAL-002",
            qr_code="MULTI-QR-002",
            status="SERVICE",
            current_customer=self.customer,
            is_active=True,
        )

        response = self.client.get(
            "/api/customers/my-ro/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            2,
        )

    # ========================================================
    # UNVERIFIED CUSTOMER BLOCKED
    # ========================================================

    def test_unverified_customer_cannot_access_my_ro(
        self
    ):

        self.user.is_verified = False

        self.user.save(
            update_fields=[
                "is_verified"
            ]
        )

        response = self.client.get(
            "/api/customers/my-ro/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    # ========================================================
    # NON CUSTOMER BLOCKED
    # ========================================================

    def test_non_customer_cannot_access_my_ro(
        self
    ):

        self.user.role = "ENGINEER"

        self.user.save(
            update_fields=[
                "role"
            ]
        )

        response = self.client.get(
            "/api/customers/my-ro/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    # ========================================================
    # NO PROFILE
    # ========================================================

    def test_customer_without_profile_gets_404(
        self
    ):

        self.customer.delete()

        response = self.client.get(
            "/api/customers/my-ro/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertFalse(
            response.data[
                "profile_exists"
            ]
        )

    # ========================================================
    # LEGACY CUSTOMER IS LINKED
    # ========================================================

    def test_legacy_customer_is_linked_by_phone(
        self
    ):

        self.customer.user = None

        self.customer.save(
            update_fields=[
                "user"
            ]
        )

        ROAsset.objects.create(
            ro_model=self.ro_model,
            serial_number="LEGACY-SERIAL",
            qr_code="LEGACY-QR",
            status="INSTALLED",
            current_customer=self.customer,
            is_active=True,
        )

        response = self.client.get(
            "/api/customers/my-ro/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.customer.refresh_from_db()

        self.assertEqual(
            self.customer.user_id,
            self.user.id,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

# ============================================================
# CUSTOMER SERVICE HISTORY TESTS
# ============================================================

class CustomerServiceHistoryTests(TestCase):

    def setUp(self):

        self.client = APIClient()

        # ----------------------------------------------------
        # CUSTOMER USER
        # ----------------------------------------------------

        self.user = User.objects.create_user(
            phone="9000000301",
            password="Test@123",
            first_name="Service",
            last_name="Customer",
            role="CUSTOMER",
            is_verified=True,
        )

        self.customer = Customer.objects.create(
            user=self.user,
            name="Service Customer",
            phone=self.user.phone,
            address="Service Address",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            ro_model="Test RO",
        )

        # ----------------------------------------------------
        # OTHER CUSTOMER
        # ----------------------------------------------------

        self.other_user = User.objects.create_user(
            phone="9000000302",
            password="Test@123",
            first_name="Other",
            last_name="Customer",
            role="CUSTOMER",
            is_verified=True,
        )

        self.other_customer = Customer.objects.create(
            user=self.other_user,
            name="Other Customer",
            phone=self.other_user.phone,
            address="Other Address",
            city="Delhi",
            state="Delhi",
            pincode="110002",
            ro_model="Other RO",
        )

        # ----------------------------------------------------
        # ENGINEER USER
        # ----------------------------------------------------

        self.engineer_user = User.objects.create_user(
            phone="9000000303",
            password="Test@123",
            first_name="Test",
            last_name="Engineer",
            role="ENGINEER",
            is_verified=True,
        )

        self.engineer = EmployeeProfile.objects.create(
            user=self.engineer_user,
            employee_id="EMP-TEST-0301",
            gender="MALE",
            joining_date=date.today(),
            designation="ENGINEER",
            salary=Decimal("25000"),
            is_active=True,
        )

        # ----------------------------------------------------
        # RO CATEGORY
        # ----------------------------------------------------

        self.ro_category = ProductCategory.objects.create(
            name="Service Test Category",
            description="Category for service history tests",
            is_active=True,
        )

        # ----------------------------------------------------
        # RO MODEL
        # ----------------------------------------------------

        self.ro_model = ROModel.objects.create(
            category=self.ro_category,
            model_name="Service Test RO",
            capacity="25 LPH",
            business_type="SALE",
            monthly_rent=Decimal("0"),
            installation_charge=Decimal("0"),
            security_deposit=Decimal("0"),
            selling_price=Decimal("10000"),
            warranty_months=12,
            is_active=True,
        )

        # ----------------------------------------------------
        # CUSTOMER RO ASSET
        # ----------------------------------------------------

        self.asset = ROAsset.objects.create(
            ro_model=self.ro_model,
            serial_number="SERVICE-RO-001",
            qr_code="SERVICE-QR-001",
            status="INSTALLED",
            current_customer=self.customer,
            is_active=True,
        )

        # ----------------------------------------------------
        # OTHER CUSTOMER RO ASSET
        # ----------------------------------------------------

        self.other_asset = ROAsset.objects.create(
            ro_model=self.ro_model,
            serial_number="SERVICE-RO-002",
            qr_code="SERVICE-QR-002",
            status="INSTALLED",
            current_customer=self.other_customer,
            is_active=True,
        )

        # ----------------------------------------------------
        # PART CATEGORY
        # ----------------------------------------------------

        self.part_category = PartCategory.objects.create(
            name="Service Test Parts",
            description="Parts for service history tests",
            is_active=True,
        )

        # ----------------------------------------------------
        # PART MASTER
        # ----------------------------------------------------

        self.part = PartMaster.objects.create(
            name="Sediment Filter",
            code="TEST-SF-001",
            category=self.part_category,
            brand="Test Brand",
            unit="PCS",
            is_serialized=False,
            warranty_months=6,
            description="Test filter",
            is_active=True,
        )

        # ----------------------------------------------------
        # SUPPLIER
        # ----------------------------------------------------

        self.supplier = Supplier.objects.create(
            name="Test Supplier",
            phone="9000000399",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            is_active=True,
        )

        # ----------------------------------------------------
        # PURCHASE
        # ----------------------------------------------------

        self.purchase = Purchase.objects.create(
            supplier=self.supplier,
            invoice_number="TEST-INV-001",
            invoice_date=date.today(),
            remarks="Service history test purchase",
        )

        # ----------------------------------------------------
        # PURCHASE ITEM
        # ----------------------------------------------------

        self.purchase_item = PurchaseItem.objects.create(
            purchase=self.purchase,
            part=self.part,
            quantity=10,
            purchase_price=Decimal("500"),
        )

        # ----------------------------------------------------
        # INVENTORY ITEM
        # ----------------------------------------------------

        self.inventory_item = InventoryItem.objects.create(
            status="INSTALLED",
            purchase_item=self.purchase_item,
            part=self.part,
            serial_number="FILTER-INV-001",
            barcode="BARCODE-001",
        )

        # ----------------------------------------------------
        # AUTHENTICATE CUSTOMER
        # ----------------------------------------------------

        self.client.force_authenticate(
            user=self.user
        )

    # ========================================================
    # HELPER
    # ========================================================

    def create_job(
        self,
        customer,
        asset,
        job_type="SERVICE",
        status="COMPLETED",
    ):

        return Job.objects.create(
            customer=customer,
            ro_asset=asset,
            engineer=self.engineer,
            job_type=job_type,
            priority="MEDIUM",
            scheduled_date=timezone.now(),
            status=status,
        )

    # ========================================================
    # CUSTOMER CAN SEE OWN SERVICE HISTORY
    # ========================================================

    def test_customer_can_see_own_service_history(
        self
    ):

        job = self.create_job(
            customer=self.customer,
            asset=self.asset,
        )

        response = self.client.get(
            f"/api/customers/{self.customer.id}/service-history/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["success"]
        )

        self.assertEqual(
            response.data["customer"]["id"],
            self.customer.id,
        )

        self.assertEqual(
            response.data["total_jobs"],
            1,
        )

        self.assertEqual(
            len(response.data["jobs"]),
            1,
        )

        self.assertEqual(
            response.data["jobs"][0]["id"],
            job.id,
        )

    # ========================================================
    # CUSTOMER CANNOT SEE OTHER CUSTOMER HISTORY
    # ========================================================

    def test_customer_cannot_see_other_customer_history(
        self
    ):

        self.create_job(
            customer=self.other_customer,
            asset=self.other_asset,
        )

        response = self.client.get(
            f"/api/customers/{self.other_customer.id}/service-history/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertFalse(
            response.data["success"]
        )

    # ========================================================
    # UNVERIFIED CUSTOMER BLOCKED
    # ========================================================

    def test_unverified_customer_cannot_access_history(
        self
    ):

        self.user.is_verified = False

        self.user.save(
            update_fields=[
                "is_verified"
            ]
        )

        self.create_job(
            customer=self.customer,
            asset=self.asset,
        )

        response = self.client.get(
            f"/api/customers/{self.customer.id}/service-history/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    # ========================================================
    # CUSTOMER CAN SEE MULTIPLE JOBS
    # ========================================================

    def test_customer_can_see_multiple_jobs(
        self
    ):

        self.create_job(
            customer=self.customer,
            asset=self.asset,
        )

        self.create_job(
            customer=self.customer,
            asset=self.asset,
            job_type="COMPLAINT",
        )

        self.create_job(
            customer=self.customer,
            asset=self.asset,
            job_type="INSTALLATION",
        )

        response = self.client.get(
            f"/api/customers/{self.customer.id}/service-history/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["total_jobs"],
            3,
        )

        self.assertEqual(
            len(response.data["jobs"]),
            3,
        )

    # ========================================================
    # PARTS USED ARE INCLUDED
    # ========================================================

    def test_service_history_includes_parts_used(
        self
    ):

        job = self.create_job(
            customer=self.customer,
            asset=self.asset,
        )

        JobPartUsed.objects.create(
            job=job,
            inventory_item=self.inventory_item,
            quantity=2,
            remarks="Filter replaced",
        )

        response = self.client.get(
            f"/api/customers/{self.customer.id}/service-history/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["total_jobs"],
            1,
        )

        self.assertEqual(
            response.data["total_parts_used"],
            2,
        )

        job_data = response.data["jobs"][0]

        self.assertEqual(
            len(job_data["parts_used"]),
            1,
        )

        self.assertEqual(
            job_data["parts_used"][0]["quantity"],
            2,
        )

    # ========================================================
    # PART QUANTITY IS SUMMED CORRECTLY
    # ========================================================

    def test_total_parts_quantity_is_correct(
        self
    ):

        job = self.create_job(
            customer=self.customer,
            asset=self.asset,
        )

        JobPartUsed.objects.create(
            job=job,
            inventory_item=self.inventory_item,
            quantity=3,
            remarks="First part",
        )

        JobPartUsed.objects.create(
            job=job,
            inventory_item=self.inventory_item,
            quantity=2,
            remarks="Second part",
        )

        response = self.client.get(
            f"/api/customers/{self.customer.id}/service-history/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["total_parts_used"],
            5,
        )

    # ========================================================
    # EMPTY SERVICE HISTORY
    # ========================================================

    def test_empty_service_history(
        self
    ):

        response = self.client.get(
            f"/api/customers/{self.customer.id}/service-history/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["success"]
        )

        self.assertEqual(
            response.data["total_jobs"],
            0,
        )

        self.assertEqual(
            response.data["total_parts_used"],
            0,
        )

        self.assertEqual(
            response.data["jobs"],
            [],
        )

    # ========================================================
    # LEGACY CUSTOMER IS LINKED BY PHONE
    # ========================================================

    def test_legacy_customer_is_linked_by_phone(
        self
    ):

        self.customer.user = None

        self.customer.save(
            update_fields=[
                "user"
            ]
        )

        self.create_job(
            customer=self.customer,
            asset=self.asset,
        )

        response = self.client.get(
            f"/api/customers/{self.customer.id}/service-history/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.customer.refresh_from_db()

        self.assertEqual(
            self.customer.user_id,
            self.user.id,
        )

        self.assertEqual(
            response.data["total_jobs"],
            1,
        )

    # ========================================================
    # NON CUSTOMER ROLE BLOCKED
    # ========================================================

    def test_non_customer_role_cannot_access_customer_history(
        self
    ):

        self.user.role = "ENGINEER"

        self.user.save(
            update_fields=[
                "role"
            ]
        )

        self.create_job(
            customer=self.customer,
            asset=self.asset,
        )

        response = self.client.get(
            f"/api/customers/{self.customer.id}/service-history/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    # ========================================================
    # CUSTOMER NOT FOUND
    # ========================================================

    def test_customer_not_found(
        self
    ):

        response = self.client.get(
            "/api/customers/999999/service-history/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )

# ============================================================
# CUSTOMER RENT & PAYMENT TESTS
# ============================================================

from decimal import Decimal
from datetime import date

from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from .models import (
    Customer,
    CustomerRentHistory,
    CustomerRentPayment,
)
from employees.models import EmployeeProfile


class CustomerRentAPITests(TestCase):

    def setUp(self):

        self.client = APIClient()

        self.customer_user = User.objects.create_user(
            phone="9100000001",
            password="Test@123",
            first_name="Rent",
            last_name="Customer",
            role="CUSTOMER",
            is_verified=True,
        )

        self.customer = Customer.objects.create(
            user=self.customer_user,
            name="Rent Customer",
            phone="9100000001",
            address="Delhi",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            ro_model="Test RO",
            monthly_rent=Decimal("500.00"),
            installation_charge=Decimal("1000.00"),
            security_deposit=Decimal("2000.00"),
            installation_date=date(2026, 8, 15),
            is_active=True,
        )

        self.staff_user = User.objects.create_user(
            phone="9100000002",
            password="Test@123",
            first_name="Office",
            last_name="Staff",
            role="OFFICE",
            is_verified=True,
        )

        self.employee = EmployeeProfile.objects.create(
            user=self.staff_user,
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="OFFICE",
            salary=Decimal("20000.00"),
        )

    # ========================================================
    # CUSTOMER RENT
    # ========================================================

    def test_customer_can_view_rent(self):

        self.client.force_authenticate(
            user=self.customer_user
        )

        response = self.client.get(
            "/api/customers/rent/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["success"]
        )

        self.assertIn(
            "current_rent",
            response.data,
        )

        self.assertIn(
            "history",
            response.data,
        )

        self.assertEqual(
            response.data["current_rent"]["expected_rent"],
            500.0,
        )

    def test_non_customer_cannot_view_customer_rent(self):

        self.client.force_authenticate(
            user=self.staff_user
        )

        response = self.client.get(
            "/api/customers/rent/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_customer_without_profile_gets_404(self):

        User.objects.create_user(
            phone="9100000003",
            password="Test@123",
            first_name="No",
            last_name="Profile",
            role="CUSTOMER",
            is_verified=True,
        )

        user = User.objects.get(
            phone="9100000003"
        )

        self.client.force_authenticate(
            user=user
        )

        response = self.client.get(
            "/api/customers/rent/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    # ========================================================
    # CURRENT RENT STATUS
    # ========================================================

    def test_new_rent_is_pending(self):

        self.client.force_authenticate(
            user=self.customer_user
        )

        response = self.client.get(
            "/api/customers/rent/"
        )

        self.assertEqual(
            response.data["current_rent"]["status"],
            "PENDING",
        )

        self.assertEqual(
            response.data["current_rent"]["paid_amount"],
            0.0,
        )

        self.assertEqual(
            response.data["current_rent"]["balance"],
            500.0,
        )

    def test_partial_payment_status(self):

        current_month = timezone.now().date().replace(
            day=1
        )

        rent = CustomerRentHistory.objects.create(
            customer=self.customer,
            rent_month=current_month,
            expected_rent=Decimal("500.00"),
            paid_amount=Decimal("200.00"),
        )

        self.client.force_authenticate(
            user=self.customer_user
        )

        response = self.client.get(
            "/api/customers/rent/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["current_rent"]["status"],
            "PARTIAL",
        )

        self.assertEqual(
            response.data["current_rent"]["paid_amount"],
            200.0,
        )

        self.assertEqual(
            response.data["current_rent"]["balance"],
            300.0,
        )

    def test_paid_status(self):

        current_month = timezone.now().date().replace(
            day=1
        )

        CustomerRentHistory.objects.create(
            customer=self.customer,
            rent_month=current_month,
            expected_rent=Decimal("500.00"),
            paid_amount=Decimal("500.00"),
        )

        self.client.force_authenticate(
            user=self.customer_user
        )

        response = self.client.get(
            "/api/customers/rent/"
        )

        self.assertEqual(
            response.data["current_rent"]["status"],
            "PAID",
        )

        self.assertEqual(
            response.data["current_rent"]["balance"],
            0.0,
        )

    # ========================================================
    # RENT MANAGEMENT
    # ========================================================

    def test_office_can_view_rent_management(self):

        self.client.force_authenticate(
            user=self.staff_user
        )

        response = self.client.get(
            "/api/customers/rent-management/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["success"]
        )

        self.assertIn(
            "customers",
            response.data,
        )

        self.assertGreaterEqual(
            response.data["count"],
            1,
        )

    def test_customer_cannot_view_rent_management(self):

        self.client.force_authenticate(
            user=self.customer_user
        )

        response = self.client.get(
            "/api/customers/rent-management/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    # ========================================================
    # PAYMENT CREATE
    # ========================================================

    def test_office_can_record_rent_payment(self):

        self.client.force_authenticate(
            user=self.staff_user
        )

        response = self.client.post(
            "/api/customers/rent-management/payment/",
            {
                "customer_id": self.customer.id,
                "amount": "200.00",
                "payment_mode": "CASH",
                "payment_date": "2026-08-18",
                "remarks": "Test payment",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertTrue(
            response.data["success"]
        )

        self.assertEqual(
            response.data["payment"]["amount"],
            200.0,
        )

        self.assertEqual(
            response.data["payment"]["payment_mode"],
            "CASH",
        )

        self.assertEqual(
            response.data["rent"]["paid_amount"],
            200.0,
        )

        self.assertEqual(
            response.data["rent"]["balance"],
            300.0,
        )

        self.assertEqual(
            response.data["rent"]["status"],
            "PARTIAL",
        )

        self.assertEqual(
            CustomerRentPayment.objects.count(),
            1,
        )

    def test_multiple_payments_accumulate(self):

        self.client.force_authenticate(
            user=self.staff_user
        )

        response1 = self.client.post(
            "/api/customers/rent-management/payment/",
            {
                "customer_id": self.customer.id,
                "amount": "200.00",
                "payment_mode": "CASH",
            },
            format="json",
        )

        self.assertEqual(
            response1.status_code,
            201,
        )

        response2 = self.client.post(
            "/api/customers/rent-management/payment/",
            {
                "customer_id": self.customer.id,
                "amount": "300.00",
                "payment_mode": "UPI",
            },
            format="json",
        )

        self.assertEqual(
            response2.status_code,
            201,
        )

        self.assertEqual(
            response2.data["rent"]["paid_amount"],
            500.0,
        )

        self.assertEqual(
            response2.data["rent"]["balance"],
            0.0,
        )

        self.assertEqual(
            response2.data["rent"]["status"],
            "PAID",
        )

        self.assertEqual(
            CustomerRentPayment.objects.count(),
            2,
        )

    def test_overpayment_is_rejected(self):

        self.client.force_authenticate(
            user=self.staff_user
        )

        response = self.client.post(
            "/api/customers/rent-management/payment/",
            {
                "customer_id": self.customer.id,
                "amount": "501.00",
                "payment_mode": "CASH",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "balance",
            response.data,
        )

        self.assertEqual(
            CustomerRentPayment.objects.count(),
            0,
        )

    def test_zero_payment_is_rejected(self):

        self.client.force_authenticate(
            user=self.staff_user
        )

        response = self.client.post(
            "/api/customers/rent-management/payment/",
            {
                "customer_id": self.customer.id,
                "amount": "0",
                "payment_mode": "CASH",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            CustomerRentPayment.objects.count(),
            0,
        )

    def test_negative_payment_is_rejected(self):

        self.client.force_authenticate(
            user=self.staff_user
        )

        response = self.client.post(
            "/api/customers/rent-management/payment/",
            {
                "customer_id": self.customer.id,
                "amount": "-100",
                "payment_mode": "CASH",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_invalid_payment_mode_is_rejected(self):

        self.client.force_authenticate(
            user=self.staff_user
        )

        response = self.client.post(
            "/api/customers/rent-management/payment/",
            {
                "customer_id": self.customer.id,
                "amount": "100",
                "payment_mode": "INVALID",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_invalid_payment_date_is_rejected(self):

        self.client.force_authenticate(
            user=self.staff_user
        )

        response = self.client.post(
            "/api/customers/rent-management/payment/",
            {
                "customer_id": self.customer.id,
                "amount": "100",
                "payment_mode": "CASH",
                "payment_date": "wrong-date",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_customer_cannot_record_payment(self):

        self.client.force_authenticate(
            user=self.customer_user
        )

        response = self.client.post(
            "/api/customers/rent-management/payment/",
            {
                "customer_id": self.customer.id,
                "amount": "100",
                "payment_mode": "CASH",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_missing_customer_id_is_rejected(self):

        self.client.force_authenticate(
            user=self.staff_user
        )

        response = self.client.post(
            "/api/customers/rent-management/payment/",
            {
                "amount": "100",
                "payment_mode": "CASH",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_missing_amount_is_rejected(self):

        self.client.force_authenticate(
            user=self.staff_user
        )

        response = self.client.post(
            "/api/customers/rent-management/payment/",
            {
                "customer_id": self.customer.id,
                "payment_mode": "CASH",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    # ========================================================
    # PAYMENT HISTORY
    # ========================================================

    def test_office_can_view_payment_history(self):

        CustomerRentHistory.objects.create(
            customer=self.customer,
            rent_month=timezone.now().date().replace(day=1),
            expected_rent=Decimal("500.00"),
            paid_amount=Decimal("200.00"),
        )

        CustomerRentPayment.objects.create(
            customer=self.customer,
            rent_history=CustomerRentHistory.objects.get(
                customer=self.customer
            ),
            amount=Decimal("200.00"),
            payment_date=timezone.now().date(),
            payment_mode="UPI",
            remarks="UPI payment",
            collected_by=self.employee,
        )

        self.client.force_authenticate(
            user=self.staff_user
        )

        response = self.client.get(
            "/api/customers/rent-management/payments/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["success"]
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

        self.assertEqual(
            response.data["payments"][0]["amount"],
            200.0,
        )

        self.assertEqual(
            response.data["payments"][0]["payment_mode"],
            "UPI",
        )

    def test_payment_history_can_filter_customer(self):

        rent = CustomerRentHistory.objects.create(
            customer=self.customer,
            rent_month=timezone.now().date().replace(day=1),
            expected_rent=Decimal("500.00"),
            paid_amount=Decimal("100.00"),
        )

        CustomerRentPayment.objects.create(
            customer=self.customer,
            rent_history=rent,
            amount=Decimal("100.00"),
            payment_date=timezone.now().date(),
            payment_mode="CASH",
            collected_by=self.employee,
        )

        self.client.force_authenticate(
            user=self.staff_user
        )

        response = self.client.get(
            f"/api/customers/rent-management/payments/"
            f"?customer_id={self.customer.id}"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

        self.assertEqual(
            response.data["payments"][0]["customer"]["id"],
            self.customer.id,
        )

    def test_customer_cannot_view_payment_history(self):

        self.client.force_authenticate(
            user=self.customer_user
        )

        response = self.client.get(
            "/api/customers/rent-management/payments/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_invalid_customer_filter_is_rejected(self):

        self.client.force_authenticate(
            user=self.staff_user
        )

        response = self.client.get(
            "/api/customers/rent-management/payments/"
            "?customer_id=abc"
        )

        self.assertEqual(
            response.status_code,
            400,
        )
