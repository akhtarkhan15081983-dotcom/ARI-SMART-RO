from django.contrib.auth.models import Permission
from rest_framework.test import APITestCase

from accounts.models import User
from .models import Customer


class CustomerEditPermissionTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone="9876511001",
            password="Test@123",
            role="ADMIN",
            is_verified=True,
        )
        self.manager = User.objects.create_user(
            phone="9876511002",
            password="Test@123",
            role="MANAGER",
            is_verified=True,
        )
        self.customer = Customer.objects.create(
            name="Permission Test Customer",
            phone="9876511003",
            address="Test Address",
            city="Ghaziabad",
            state="UP",
            pincode="201001",
            ro_model="ARI RO",
        )

    def _patch_name(self, user, name):
        self.client.force_authenticate(user)
        return self.client.patch(
            f"/api/customers/{self.customer.id}/update/",
            {"name": name},
            format="json",
        )

    def test_admin_can_edit_customer_without_delegation(self):
        response = self._patch_name(self.admin, "Admin Updated")
        self.assertEqual(response.status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.name, "Admin Updated")

    def test_manager_cannot_edit_customer_by_default(self):
        response = self._patch_name(self.manager, "Manager Updated")
        self.assertEqual(response.status_code, 403)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.name, "Permission Test Customer")

    def test_admin_delegated_user_can_edit_customer(self):
        permission = Permission.objects.get(
            codename="change_customer",
            content_type__app_label="customers",
            content_type__model="customer",
        )
        self.manager.user_permissions.add(permission)

        response = self._patch_name(self.manager, "Delegated Updated")
        self.assertEqual(response.status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.name, "Delegated Updated")

    def test_capability_endpoint_matches_effective_permission(self):
        self.client.force_authenticate(self.manager)
        response = self.client.get("/api/customers/edit-permission/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["can_edit_customer"])

        permission = Permission.objects.get(
            codename="change_customer",
            content_type__app_label="customers",
            content_type__model="customer",
        )
        self.manager.user_permissions.add(permission)
        self.manager = User.objects.get(pk=self.manager.pk)
        self.client.force_authenticate(self.manager)

        response = self.client.get("/api/customers/edit-permission/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["can_edit_customer"])
