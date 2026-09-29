from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from employees.models import EmployeeProfile
from tenancy.access import request_company

from .views import ComplaintAssignEngineerAPIView, ComplaintUpdateAPIView


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
            return super().patch(request, pk)

        if not EmployeeProfile.objects.filter(
            pk=engineer_id,
            company=company,
            is_active=True,
            user__is_active=True,
            designation="ENGINEER",
        ).exists():
            return Response(
                {"success": False, "message": "Active engineer not found in this workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return super().patch(request, pk)


class SecureComplaintUpdateAPIView(ComplaintUpdateAPIView):
    """Allow note/schedule edits without bypassing secured complaint workflow endpoints."""

    protected_fields = {
        "customer",
        "engineer",
        "status",
        "resolved_date",
        "job",
        "linked_service",
    }

    def perform_update(self, serializer):
        attempted = sorted(
            field for field in self.protected_fields if field in serializer.validated_data
        )
        if attempted:
            raise ValidationError({
                "detail": (
                    "Complaint ownership, assignment and workflow state must be changed "
                    "through the dedicated secured endpoints."
                ),
                "protected_fields": attempted,
            })
        serializer.save()
