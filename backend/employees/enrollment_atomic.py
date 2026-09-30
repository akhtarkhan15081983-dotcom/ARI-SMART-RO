from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from .models import EmployeeProfile
from .reliability import SecureFaceEnrollmentAPIView


class TransactionSafeFaceEnrollmentAPIView(SecureFaceEnrollmentAPIView):
    """Serialize one employee's face/device enrollment through final save.

    SecureFaceEnrollmentAPIView remains the security authority for login-device
    matching and audit events. This wrapper only adds transaction/row-lock
    semantics so concurrent retries cannot consume the same re-enrollment grant
    or leave face/device database state split across requests.
    """

    @transaction.atomic
    def post(self, request):
        try:
            EmployeeProfile.objects.select_for_update().get(user=request.user)
        except EmployeeProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "Employee profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().post(request)
