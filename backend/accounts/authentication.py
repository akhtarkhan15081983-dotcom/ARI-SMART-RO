from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

from .token_security import token_session_is_current


class VerifiedCustomerJWTAuthentication(JWTAuthentication):
    TENANT_SAFE_PREFIXES = (
        "/api/auth/",
        "/api/saas/",
        "/api/employees/manage/",
    )

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, token = result

        if not token_session_is_current(user, token):
            raise AuthenticationFailed(
                "Your secure session has expired. Please sign in again.",
                code="session_revoked",
            )

        if user.is_superuser or user.role == "CUSTOMER":
            return user, token

        if user.role != "ADMIN":
            device_id = str(request.headers.get("X-ARI-Device-ID", "") or "").strip()[:64]
            bound_device_id = str(getattr(user, "active_login_device_id", "") or "").strip()
            if not bound_device_id:
                raise AuthenticationFailed(
                    "Employee login device has been reset. Please sign in again.",
                    code="employee_device_login_required",
                )
            if not device_id or device_id != bound_device_id:
                raise AuthenticationFailed(
                    "This employee session belongs to another phone.",
                    code="employee_device_mismatch",
                )

        membership = (
            user.company_memberships.filter(is_active=True)
            .select_related("company")
            .first()
        )
        if (
            membership
            and membership.company.slug != "ari-smart-ro"
            and not request.path.startswith(self.TENANT_SAFE_PREFIXES)
        ):
            raise PermissionDenied(
                "This company workspace is securely isolated and is awaiting operational data provisioning.",
                code="tenant_operational_data_not_provisioned",
            )
        return user, token

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if user.role == "CUSTOMER" and not user.is_verified:
            raise AuthenticationFailed(
                "Phone verification is required before customer access.",
                code="customer_phone_not_verified",
            )
        return user
