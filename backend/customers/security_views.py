from rest_framework import status
from rest_framework.response import Response

from employees.models import EmployeeProfile
from tenancy.access import request_company

from .views import AssignCustomerAPIView


class TenantScopedAssignCustomerAPIView(AssignCustomerAPIView):
    """Limit customer assignment targets to staff in the current workspace."""

    def post(self, request, pk):
        company = request_company(request)
        if company is None:
            return Response(
                {"detail": "Active company workspace not found."},
                status=status.HTTP_403_FORBIDDEN,
            )

        employee_id = request.data.get("employee_id", request.data.get("engineer"))
        try:
            employee_id = int(employee_id)
        except (TypeError, ValueError):
            return super().post(request, pk)

        if not EmployeeProfile.objects.filter(
            pk=employee_id,
            company=company,
            is_active=True,
            user__is_active=True,
            user__role__in=["ENGINEER", "OFFICE"],
        ).exists():
            return Response(
                {"message": "Employee not found in this workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return super().post(request, pk)
