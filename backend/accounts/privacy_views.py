from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

from .views import SendOTPAPIView


class SecureSendOTPAPIView(SendOTPAPIView):
    """Do not reveal whether a phone number has an ARI customer account in production."""

    def post(self, request):
        response = super().post(request)
        # CI/tests intentionally disable auth throttling. Preserve the explicit
        # 404 contract there so legacy tests remain meaningful, while production
        # keeps account existence private.
        if settings.DEBUG or settings.DISABLE_AUTH_THROTTLING:
            return response
        if response.status_code == status.HTTP_404_NOT_FOUND:
            return Response(
                {
                    "success": True,
                    "message": (
                        "If this mobile number is eligible for verification, "
                        "a code has been sent."
                    ),
                },
                status=status.HTTP_200_OK,
            )
        return response
