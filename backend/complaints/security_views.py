from rest_framework import status
from rest_framework.response import Response

from employees.models import EmployeeProfile
from tenancy.access import request_company

from .views import ComplaintAssignEngineerAPIView


class TenantScopedComplaintAssignEngineerAPIView(ComplaintAssignEngineerAPIView):
    """Prevent operational staff from assigning a complaint to another tenant."""

    def patch(self, request, pk):
        company = request_company(request)
        if company is None:
            return Response(
                {"success": False, "message": "Active company workspace not found."},
                status=status.HTTP_403_FORBIDDEN,
            )

        engineer_id = request.data.get("engineer")
        try:
            engineer_id = int(engineer_id)
        except (TypeError, ValueError):
            # Preserve the base view's detailed validation response.
            return super().patch(request, pk)

        if not EmployeeProfile.objects.filter(
            pk=engineer_id,
            company=company,
            is_active=True,
            user__is_active=True,
            designation="ENGINEER",
        ).exists():
            # Deliberately do not reveal whether the supplied ID belongs to a
            # different tenant.
            return Response(
                {"success": False, "message": "Active engineer not found in this workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return super().patch(request, pk)
