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
        engineer_id = request.data.get("engineer")
        try:
            engineer_id = int(engineer_id)
        except (TypeError, ValueError):
            return super().patch(request, pk)

        engineer_scope = EmployeeProfile.objects.filter(
            pk=engineer_id,
            is_active=True,
            user__is_active=True,
            designation="ENGINEER",
        )
        if company is not None:
            engineer_scope = engineer_scope.filter(company=company)
        else:
            engineer_scope = engineer_scope.filter(company__isnull=True)

        if not engineer_scope.exists():
            return Response(
                {"success": False, "message": "Active engineer not found in this workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return super().patch(request, pk)


class SecureComplaintUpdateAPIView(ComplaintUpdateAPIView):
    """Allow safe metadata edits and same-workspace reassignment only.

    Workflow state, ownership and linked job/service relations remain dedicated-
    endpoint concerns. Reassignment through the legacy generic update endpoint
    is retained for compatibility, but its target is tenant validated first.
    """

    protected_fields = {
        "customer",
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
                    "Complaint ownership and workflow state must be changed "
                    "through the dedicated secured endpoints."
                ),
                "protected_fields": attempted,
            })

        engineer = serializer.validated_data.get("engineer")
        if engineer is not None:
            company = request_company(self.request)
            if not engineer.is_active or not engineer.user.is_active or engineer.designation != "ENGINEER":
                raise ValidationError({"engineer": ["Active engineer is required."]})
            if company is not None:
                if engineer.company_id != company.id:
                    raise ValidationError({"engineer": ["Engineer is outside the active workspace."]})
            elif engineer.company_id is not None:
                raise ValidationError({"engineer": ["Engineer is outside the legacy workspace."]})

        serializer.save()
