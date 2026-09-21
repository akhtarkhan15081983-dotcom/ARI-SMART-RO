from rest_framework.permissions import BasePermission, SAFE_METHODS


STAFF_ROLES = {"ADMIN", "MANAGER", "OFFICE"}
OPERATIONS_ROLES = STAFF_ROLES | {"ENGINEER"}


def user_role(user):
    return str(getattr(user, "role", "") or "").strip().upper()


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and user_role(request.user) == "ADMIN"
        )


class IsAdminOrManager(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and user_role(request.user) in {"ADMIN", "MANAGER"}
        )


def can_edit_customers(user):
    """Customer master data may be changed only by Admin or an explicitly delegated user."""
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and (
            user_role(user) == "ADMIN"
            or user.has_perm("customers.change_customer")
        )
    )


class CanEditCustomer(BasePermission):
    def has_permission(self, request, view):
        return can_edit_customers(request.user)


class IsEngineer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and user_role(request.user) == "ENGINEER"
        )


class IsStaffOperator(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and user_role(request.user) in STAFF_ROLES
        )


class IsOperationsUser(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and user_role(request.user) in OPERATIONS_ROLES
        )


class IsReadOnlyOrStaffOperator(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.method in SAFE_METHODS or user_role(request.user) in STAFF_ROLES


class IsVerifiedCustomer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and user_role(request.user) == "CUSTOMER"
            and request.user.is_verified
            and request.user.is_active
        )


class IsVerifiedCustomerOrOperations(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = user_role(request.user)
        if role == "CUSTOMER":
            return bool(request.user.is_verified and request.user.is_active)
        return role in OPERATIONS_ROLES
