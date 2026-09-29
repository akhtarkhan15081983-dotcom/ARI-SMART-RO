from rest_framework import status
from rest_framework.response import Response

from tenancy.access import request_company

from .models import Job
from .views import AdminJobOTPAPIView


class TenantScopedAdminJobOTPAPIView(AdminJobOTPAPIView):
    """Ensure audited emergency OTP access cannot cross company boundaries."""

    def get(self, request, pk):
        company = request_company(request)
        if company is None:
            return Response(
                {"detail": "Active company workspace not found."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not Job.objects.filter(
            pk=pk,
            engineer__company=company,
            engineer__is_active=True,
            engineer__user__is_active=True,
        ).exists():
            return Response(
                {"detail": "Job not found in this workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return super().get(request, pk)
