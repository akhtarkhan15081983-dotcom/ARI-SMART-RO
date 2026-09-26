from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

from .views import SendOTPAPIView


class SecureSendOTPAPIView(SendOTPAPIView):
    """Do not reveal whether a phone number has an ARI customer account."""

    def post(self, request):
        response = super().post(request)
        if settings.DEBUG:
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
