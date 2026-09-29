from rest_framework import status
from rest_framework.response import Response

from employees.models import EmployeeProfile
from tenancy.access import request_company

from .models import PartRequest
from .views import (
    AdminEngineerBagAPIView,
    EngineerBagIssueAPIView,
    PartRequestApprovalInboxAPIView,
    PartRequestFulfilAPIView,
    PartRequestReviewAPIView,
)


def _employee_in_request_workspace(request, employee_id):
    company = request_company(request)
    queryset = EmployeeProfile.objects.filter(
        pk=employee_id,
        is_active=True,
        user__is_active=True,
    )
    if company is not None:
        return queryset.filter(company=company).exists()
    return queryset.filter(company__isnull=True).exists()


def _part_request_in_request_workspace(request, request_id):
    company = request_company(request)
    queryset = PartRequest.objects.filter(pk=request_id)
    if company is not None:
        return queryset.filter(engineer__company=company).exists()
    return queryset.filter(engineer__company__isnull=True).exists()


class TenantScopedEngineerBagIssueAPIView(EngineerBagIssueAPIView):
    """Prevent stock issue to an employee outside the active workspace."""

    def create(self, request, *args, **kwargs):
        engineer_id = request.data.get("engineer")
        try:
            engineer_id = int(engineer_id)
        except (TypeError, ValueError):
            return super().create(request, *args, **kwargs)

        if not _employee_in_request_workspace(request, engineer_id):
            return Response(
                {"error": "Engineer not found in this workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().create(request, *args, **kwargs)


class TenantScopedAdminEngineerBagAPIView(AdminEngineerBagAPIView):
    """Admin/Manager bag visibility is limited to their active workspace."""

    def get_queryset(self):
        queryset = super().get_queryset()
        company = request_company(self.request)
        if company is not None:
            return queryset.filter(engineer__company=company)
        return queryset.filter(engineer__company__isnull=True)


class TenantScopedPartRequestApprovalInboxAPIView(PartRequestApprovalInboxAPIView):
    """Never fall back to an all-company approval inbox."""

    def get(self, request):
        company = request_company(request)
        queryset = PartRequest.objects.select_related("part", "engineer__user").order_by("-created_at")
        if company is not None:
            queryset = queryset.filter(engineer__company=company)
        else:
            queryset = queryset.filter(engineer__company__isnull=True)

        status_filter = str(request.query_params.get("status", "")).upper()
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        from .views import _request_payload
        return Response({"success": True, "requests": [_request_payload(row) for row in queryset[:250]]})


class TenantScopedPartRequestReviewAPIView(PartRequestReviewAPIView):
    def post(self, request, request_id):
        if not _part_request_in_request_workspace(request, request_id):
            return Response(
                {"success": False, "message": "Part request not found in this workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().post(request, request_id)


class TenantScopedPartRequestFulfilAPIView(PartRequestFulfilAPIView):
    def post(self, request, request_id):
        if not _part_request_in_request_workspace(request, request_id):
            return Response(
                {"success": False, "message": "Part request not found in this workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().post(request, request_id)
