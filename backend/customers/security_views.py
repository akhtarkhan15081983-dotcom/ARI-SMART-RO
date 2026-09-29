from rest_framework import status
from rest_framework.response import Response

from employees.models import EmployeeProfile
from tenancy.access import request_company

from .views import AssignCustomerAPIView


class TenantScopedAssignCustomerAPIView(AssignCustomerAPIView):
    """Limit customer assignment targets to staff in the current workspace."""

    def post(self, request, pk):
        company = request_company(request)

        employee_id = request.data.get("employee_id", request.data.get("engineer"))
        try:
            employee_id = int(employee_id)
        except (TypeError, ValueError):
            return super().post(request, pk)

        employee_scope = EmployeeProfile.objects.filter(
            pk=employee_id,
            is_active=True,
            user__is_active=True,
            user__role__in=["ENGINEER", "OFFICE"],
        )
        if company is not None:
            employee_scope = employee_scope.filter(company=company)
        else:
            # Backward-compatible path for records created before tenancy was
            # introduced. A tenant-less actor may only target a tenant-less
            # employee; it can never cross into a real company workspace.
            employee_scope = employee_scope.filter(company__isnull=True)

        if not employee_scope.exists():
            return Response(
                {"message": "Employee not found in this workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return super().post(request, pk)
