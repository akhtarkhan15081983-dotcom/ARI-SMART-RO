from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class VerifiedCustomerJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if user.role == "CUSTOMER" and not user.is_verified:
            raise AuthenticationFailed(
                "Phone verification is required before customer access.",
                code="customer_phone_not_verified",
            )
        return user
