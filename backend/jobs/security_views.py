from rest_framework import status
from rest_framework.response import Response

from tenancy.access import request_company

from .models import Job
from .views import AdminJobOTPAPIView


class TenantScopedAdminJobOTPAPIView(AdminJobOTPAPIView):
    """Ensure audited emergency OTP access cannot cross company boundaries."""

    def get(self, request, pk):
        company = request_company(request)

        job_scope = Job.objects.filter(
            pk=pk,
            engineer__is_active=True,
            engineer__user__is_active=True,
        )
        if company is not None:
            job_scope = job_scope.filter(engineer__company=company)
        else:
            # Legacy pre-tenancy fixtures/accounts remain usable only against
            # jobs whose assigned engineer is also tenant-less. This never
            # grants access into a company-bound workspace.
            job_scope = job_scope.filter(engineer__company__isnull=True)

        if not job_scope.exists():
            return Response(
                {"detail": "Job not found in this workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return super().get(request, pk)
