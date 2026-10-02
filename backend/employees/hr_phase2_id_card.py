from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import hr_lifecycle
from . import hr_phase1 as _hr_phase1  # noqa: F401
from . import hr_phase1_requirements as _hr_phase1_requirements  # noqa: F401
from .hr_lifecycle_models import EmployeeHrLifecycle
from .models import EmployeeProfile
from .views import (
    EmployeeManagementAPIView as BaseEmployeeManagementAPIView,
    _employee_id_card_payload,
)


_CARD_VALIDITY_DAYS = 365 * 3
_prior_readiness = hr_lifecycle._readiness


def _issue_card_if_fully_ready(employee, readiness):
    """Issue a card once, only after non-override corporate readiness succeeds."""
    if not readiness.get("ready_without_override"):
        return False
    if employee.id_card_issued_at is not None:
        return False
    employee.id_card_issued_at = timezone.now()
    employee.id_card_valid_until = timezone.localdate() + timedelta(days=_CARD_VALIDITY_DAYS)
    employee.save(update_fields=["id_card_issued_at", "id_card_valid_until"])
    return True


def _readiness_with_id_card_issue(employee, lifecycle):
    readiness = _prior_readiness(employee, lifecycle)
    _issue_card_if_fully_ready(employee, readiness)
    return readiness


# All existing readiness call sites now issue the employee card idempotently when
# the full (non-admin-override) Ready-for-Duty contract is genuinely satisfied.
hr_lifecycle._readiness = _readiness_with_id_card_issue


def _corporate_card_payload(request, employee):
    lifecycle, _ = EmployeeHrLifecycle.objects.get_or_create(employee=employee)
    readiness = hr_lifecycle._readiness(employee, lifecycle)
    payload = _employee_id_card_payload(request, employee)

    issued = employee.id_card_issued_at is not None
    active = bool(issued and employee.is_active and employee.user.is_active)
    if not issued:
        card_status = "NOT_ISSUED"
    elif active:
        card_status = "ISSUED"
    else:
        card_status = "INACTIVE"

    payload.update(
        {
            "issued": issued,
            "status": card_status,
            "active": active,
            "readiness_qualified": bool(readiness.get("ready_without_override")),
            "corporate_readiness": readiness,
        }
    )
    return payload


class EmployeeManagementAPIView(BaseEmployeeManagementAPIView):
    """Preserve employee-number reservation but do not issue the ID card at creation."""

    @transaction.atomic
    def post(self, request):
        response = super().post(request)
        if response.status_code != 201:
            return response

        employee_id = ((response.data or {}).get("employee") or {}).get("id")
        employee = EmployeeProfile.objects.filter(pk=employee_id).first()
        if employee is not None and (
            employee.id_card_issued_at is not None or employee.id_card_valid_until is not None
        ):
            employee.id_card_issued_at = None
            employee.id_card_valid_until = None
            employee.save(update_fields=["id_card_issued_at", "id_card_valid_until"])
        return response


class EmployeeIdCardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = (
            EmployeeProfile.objects.filter(user=request.user)
            .select_related("user", "company")
            .first()
        )
        if employee is None:
            return Response({"detail": "Employee profile not found."}, status=404)
        return Response(_corporate_card_payload(request, employee))


class EmployeeIdVerifyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, code):
        employee = (
            EmployeeProfile.objects.filter(
                public_verification_code=str(code).strip().upper(),
            )
            .select_related("user", "company")
            .first()
        )
        if employee is None:
            return Response({"verified": False, "detail": "Employee ID not found."}, status=404)
        payload = _corporate_card_payload(request, employee)
        return Response({"verified": bool(payload["active"]), "employee": payload})
