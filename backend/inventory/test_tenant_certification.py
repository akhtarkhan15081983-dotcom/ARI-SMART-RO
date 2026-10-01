from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from employees.models import EmployeeProfile
from inventory.models import EngineerBagItem, InventoryItem, PartRequest
from partmaster.models import PartCategory, PartMaster
from purchase.models import Purchase, PurchaseItem, Supplier
from tenancy.models import Company, CompanyMembership


class InventoryTenantCertificationTests(TestCase):
    def setUp(self):
        self.company_a = Company.objects.create(
            name="Inventory Tenant A",
            slug="inventory-tenant-a-cert",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.company_b = Company.objects.create(
            name="Inventory Tenant B",
            slug="inventory-tenant-b-cert",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.user_a = User.objects.create_user(
            phone="9333390001",
            password="Strong@123",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        self.user_b = User.objects.create_user(
            phone="9333390002",
            password="Strong@123",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company_a,
            user=self.user_a,
            role="STAFF",
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company_b,
            user=self.user_b,
            role="STAFF",
            is_active=True,
        )
        self.engineer_a = EmployeeProfile.objects.create(
            company=self.company_a,
            user=self.user_a,
            employee_id="INV-A",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            is_active=True,
        )
        self.engineer_b = EmployeeProfile.objects.create(
            company=self.company_b,
            user=self.user_b,
            employee_id="INV-B",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            is_active=True,
        )
        category = PartCategory.objects.create(name="Inventory Tenant Cert")
        self.part = PartMaster.objects.create(
            name="Tenant Pump",
            code="TEN-PUMP",
            category=category,
            is_serialized=True,
        )
        self.mine = PartRequest.objects.create(
            company=self.company_a,
            engineer=self.engineer_a,
            part=self.part,
            quantity=1,
        )
        self.malformed_other = PartRequest.objects.create(
            company=self.company_b,
            engineer=self.engineer_a,
            part=self.part,
            quantity=1,
        )

        supplier = Supplier.objects.create(name="Tenant QR Supplier")
        purchase = Purchase.objects.create(
            company=self.company_b,
            supplier=supplier,
            invoice_number="TENANT-QR-1",
            invoice_date=date(2026, 9, 1),
        )
        purchase_item = PurchaseItem.objects.create(
            company=self.company_b,
            purchase=purchase,
            part=self.part,
            quantity=1,
            purchase_price="100.00",
        )
        other_item = InventoryItem.objects.create(
            company=self.company_b,
            purchase_item=purchase_item,
            part=self.part,
            serial_number="OTHER-TENANT-SERIAL",
            status="ISSUED",
        )
        EngineerBagItem.objects.create(
            company=self.company_b,
            engineer=self.engineer_b,
            inventory_item=other_item,
            status="ISSUED",
        )

        self.client = APIClient()
        self.client.force_authenticate(self.user_a)

    def test_my_part_requests_exclude_cross_tenant_row(self):
        response = self.client.get("/api/inventory/part-requests/")

        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.data}
        self.assertIn(self.mine.id, ids)
        self.assertNotIn(self.malformed_other.id, ids)

    def test_qr_verification_does_not_signal_other_tenant_serial(self):
        response = self.client.post(
            "/api/inventory/verify/",
            {
                "engineer": self.engineer_a.id,
                "serial_number": "OTHER-TENANT-SERIAL",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["verified"])


    def test_my_bag_excludes_cross_tenant_items(self):
        supplier = Supplier.objects.create(name="Tenant A Bag Supplier")
        purchase = Purchase.objects.create(
            company=self.company_a,
            supplier=supplier,
            invoice_number="TENANT-BAG-A-1",
            invoice_date=date(2026, 9, 2),
        )
        purchase_item = PurchaseItem.objects.create(
            company=self.company_a,
            purchase=purchase,
            part=self.part,
            quantity=1,
            purchase_price="100.00",
        )
        own_item = InventoryItem.objects.create(
            company=self.company_a,
            purchase_item=purchase_item,
            part=self.part,
            serial_number="OWN-TENANT-SERIAL",
            status="ISSUED",
        )
        own_bag = EngineerBagItem.objects.create(
            company=self.company_a,
            engineer=self.engineer_a,
            inventory_item=own_item,
            status="ISSUED",
        )

        response = self.client.get("/api/inventory/my-bag/")

        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.data}
        self.assertIn(own_bag.id, ids)
        self.assertEqual(len(ids), 1)

    def test_admin_engineer_bag_list_is_tenant_scoped(self):
        admin = User.objects.create_user(
            phone="9333390009",
            password="Strong@123",
            role="ADMIN",
            is_verified=True,
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company_a,
            user=admin,
            role="OWNER",
            is_active=True,
        )
        self.client.force_authenticate(admin)

        response = self.client.get("/api/inventory/admin/engineer-bags/")

        self.assertEqual(response.status_code, 200)
        engineer_ids = {row["engineer_id"] for row in response.data}
        self.assertNotIn(self.engineer_b.id, engineer_ids)
