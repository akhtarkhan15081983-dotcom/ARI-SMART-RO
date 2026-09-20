from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import BasePermission

from .models import CompanyMembership, RoleFeaturePermission


ROLE_FEATURE_CATALOG = {
    "attendance": "Attendance",
    "hrms": "Employee HRMS",
    "work_calendar": "Work Calendar",
    "work_route": "Work Route",
    "jobs": "Jobs",
    "assigned_customers": "Assigned Customers",
    "customers": "Customers",
    "walkin": "Walk-In Installation",
    "service": "Service",
    "bag": "Engineer Bag",
    "request": "Part Request",
    "qr": "QR Verification",
    "rent_management": "Rent Management",
    "payment_history": "Payment History",
    "complaint": "Complaint",
    "referral": "Refer & Wallet",
    "profile": "Profile",
    "reports": "Business Reports",
    "inventory_workflow": "Inventory Control",
    "calling_desk": "Calling Desk",
    "map": "Live Map",
    "engineer_map": "Engineer Live Location",
    "employee_management": "Employee Management",
    "performance_admin": "Performance Management",
    "documents_admin": "Document Compliance",
    "hrms_leave_approve": "HRMS • Leave Approval",
    "hrms_holiday_manage": "HRMS • Holiday Management",
    "hrms_payroll_manage": "HRMS • Payroll Approve/Pay",
    "hrms_penalty_manage": "HRMS • Penalty Management",
    "hrms_performance_manage": "HRMS • Performance Finalize",
    "hrms_documents_manage": "HRMS • Document Management",
    "employee_career_manage": "Employees • Promotion/Career Changes",
}

DEFAULT_ROLE_FEATURES = {
    "MANAGER": {
        "attendance", "hrms", "work_calendar", "work_route", "jobs",
        "assigned_customers", "customers", "walkin", "service", "bag",
        "request", "qr", "rent_management", "payment_history", "complaint",
        "referral", "profile", "reports", "inventory_workflow", "calling_desk",
        "map", "engineer_map", "performance_admin", "documents_admin",
        "hrms_leave_approve", "hrms_performance_manage", "hrms_holiday_manage",
    },
    "OFFICE": {
        "attendance", "hrms", "customers", "walkin", "service",
        "rent_management", "payment_history", "reports", "inventory_workflow",
        "work_calendar", "work_route", "complaint", "referral", "profile",
        "calling_desk", "documents_admin", "hrms_documents_manage",
        "hrms_holiday_manage",
    },
    "CALLING": {"attendance", "hrms", "calling_desk", "profile"},
    "ENGINEER": {
        "attendance", "hrms", "work_calendar", "work_route", "jobs",
        "assigned_customers", "customers", "walkin", "service", "bag",
        "request", "qr", "rent_management", "complaint", "referral", "profile",
    },
}


def request_company(request):
    membership = (
        CompanyMembership.objects.filter(
            user=request.user,
            is_active=True,
            company__is_active=True,
            company__lifecycle_status="ACTIVE",
        )
        .select_related("company")
        .first()
    )
    if membership:
        return membership.company

    # Backward-compatible fallback for operational employee accounts created
    # before CompanyMembership became mandatory.
    try:
        company = request.user.employee_profile.company
    except (AttributeError, ObjectDoesNotExist):
        return None
    if company and company.is_active and company.lifecycle_status == "ACTIVE":
        return company
    return None


def effective_role_features(company, role):
    role = str(role or "").strip().upper()
    if role == "ADMIN":
        return set(ROLE_FEATURE_CATALOG.keys())
    defaults = set(DEFAULT_ROLE_FEATURES.get(role, set()))
    overrides = RoleFeaturePermission.objects.filter(company=company, role=role)
    for row in overrides:
        if row.is_allowed:
            defaults.add(row.feature_key)
        else:
            defaults.discard(row.feature_key)
    return defaults


def has_feature_access(request, feature_key):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not user.is_active:
        return False
    role = str(getattr(user, "role", "") or "").strip().upper()
    if role == "ADMIN":
        return True
    company = request_company(request)
    if company is None:
        # Legacy employee accounts created before multi-company tenancy may
        # not have a CompanyMembership yet. Preserve their original role
        # permissions while keeping company-specific overrides for migrated
        # accounts.
        return feature_key in DEFAULT_ROLE_FEATURES.get(role, set())
    return feature_key in effective_role_features(company, role)



class HasRequiredFeature(BasePermission):
    def has_permission(self, request, view):
        feature_key = getattr(view, "required_feature", "")
        if not feature_key:
            return False
        return has_feature_access(request, feature_key)
