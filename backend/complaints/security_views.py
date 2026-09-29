from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from employees.models import EmployeeProfile
from tenancy.access import request_company

from .models import Complaint
from .views import ComplaintAssignEngineerAPIView, ComplaintUpdateAPIView


def _complaint_company_id(row):
    explicit = row.company_id
    customer_company = getattr(row.customer, "company_id", None)
    assigned_company = (
        row.customer.assigned_engineer.company_id
        if getattr(row.customer, "assigned_engineer_id", None)
        else None
    )
    candidates = {value for value in (explicit, customer_company, assigned_company) if value is not None}
    if len(candidates) > 1:
        raise ValidationError({"detail": "Complaint ownership evidence conflicts across companies."})
    return next(iter(candidates)) if candidates else None


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

        complaint = Complaint.objects.select_related(
            "customer__assigned_engineer"
        ).filter(pk=pk).first()
        if complaint is None:
            return Response(
                {"success": False, "message": "Complaint not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        effective_company_id = _complaint_company_id(complaint)
        if company is not None:
            if effective_company_id not in (None, company.id):
                return Response(
                    {"success": False, "message": "Complaint not found in this workspace."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if complaint.company_id is None:
                complaint.company = company
                complaint.save(update_fields=["company"])
        elif effective_company_id is not None:
            return Response(
                {"success": False, "message": "Complaint not found in the legacy workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return super().patch(request, pk)


class SecureComplaintUpdateAPIView(ComplaintUpdateAPIView):
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

        instance = self.get_object()
        company = request_company(self.request)
        effective_company_id = _complaint_company_id(instance)
        if company is not None:
            if effective_company_id not in (None, company.id):
                raise ValidationError({"detail": "Complaint belongs to another company workspace."})
        elif effective_company_id is not None:
            raise ValidationError({"detail": "Complaint belongs to another company workspace."})

        engineer = serializer.validated_data.get("engineer")
        if engineer is not None:
            if not engineer.is_active or not engineer.user.is_active or engineer.designation != "ENGINEER":
                raise ValidationError({"engineer": ["Active engineer is required."]})
            if company is not None:
                if engineer.company_id != company.id:
                    raise ValidationError({"engineer": ["Engineer is outside the active workspace."]})
            elif engineer.company_id is not None:
                raise ValidationError({"engineer": ["Engineer is outside the legacy workspace."]})

        if company is not None:
            serializer.save(company=company)
        else:
            serializer.save()
