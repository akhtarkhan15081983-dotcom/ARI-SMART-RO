from django.db import transaction
from rest_framework.response import Response

from tenancy.access import has_feature_access, request_company

from .hr_phase2_letters_bgv import (
    DEFAULT_REQUIRED_BGV,
    BGV_CHECK_TYPES,
    BackgroundVerificationCaseAPIView as BaseBackgroundVerificationCaseAPIView,
    BgvPolicyAPIView as BaseBgvPolicyAPIView,
    _audit,
    _case_payload,
    _employee,
)
from .hr_phase2_letters_bgv_models import BackgroundVerificationCase, BgvPolicy
from .hr_phase2_recruitment_models import CandidateApplication


def _boolean(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class BgvPolicyAPIView(BaseBgvPolicyAPIView):
    @transaction.atomic
    def patch(self, request):
        if not has_feature_access(request, "hrms_bgv_override"):
            return Response({"detail": "BGV override/policy permission is required."}, status=403)
        company = request_company(request)
        if company is None:
            return Response({"detail": "Active company workspace is required."}, status=403)
        mandatory = _boolean(request.data.get("mandatory_before_ready"))
        required = request.data.get("required_checks")
        if required is None:
            required = DEFAULT_REQUIRED_BGV if mandatory else []
        if not isinstance(required, list) or any(str(item).upper() not in BGV_CHECK_TYPES for item in required):
            return Response({"detail": "required_checks must contain valid BGV check types."}, status=400)
        row, _ = BgvPolicy.objects.get_or_create(company=company, defaults={"updated_by": request.user})
        before = row.mandatory_before_ready
        row.mandatory_before_ready = mandatory
        row.required_checks = list(dict.fromkeys(str(item).upper() for item in required))
        row.updated_by = request.user
        row.save()
        _audit(
            request,
            company=company,
            entity_type="BGV_POLICY",
            entity_id=row.id,
            action="UPDATED",
            from_status=str(before),
            to_status=str(mandatory),
            metadata={"required_checks": row.required_checks},
        )
        return Response({"mandatory_before_ready": mandatory, "required_checks": row.required_checks})


class BackgroundVerificationCaseAPIView(BaseBackgroundVerificationCaseAPIView):
    @transaction.atomic
    def post(self, request):
        if not has_feature_access(request, "hrms_bgv_manage"):
            return Response({"detail": "BGV management permission is required."}, status=403)
        company = request_company(request)
        if company is None:
            return Response({"detail": "Active company workspace is required."}, status=403)
        application = None
        employee = None
        candidate = None
        if request.data.get("application_id"):
            application = (
                CandidateApplication.objects.filter(
                    company=company,
                    pk=request.data.get("application_id"),
                )
                .select_related("candidate", "converted_employee")
                .first()
            )
            if application is None:
                return Response({"detail": "Candidate application not found in this company."}, status=404)
            candidate = application.candidate
            employee = application.converted_employee
            existing = BackgroundVerificationCase.objects.filter(company=company, application=application).first()
        elif request.data.get("employee_id"):
            employee = _employee(company, request.data.get("employee_id"))
            if employee is None:
                return Response({"detail": "Employee not found in this company."}, status=404)
            source_application = getattr(employee, "source_candidate_application", None)
            if source_application:
                application = source_application
                candidate = source_application.candidate
                existing = BackgroundVerificationCase.objects.filter(company=company, application=application).first()
            else:
                existing = BackgroundVerificationCase.objects.filter(company=company, employee=employee).first()
        else:
            return Response({"detail": "application_id or employee_id is required."}, status=400)
        if existing:
            return Response({**_case_payload(existing), "idempotent": True})
        row = BackgroundVerificationCase.objects.create(
            company=company,
            candidate=candidate,
            application=application,
            employee=employee,
            overall_status="NOT_STARTED",
            created_by=request.user,
        )
        _audit(
            request,
            company=company,
            entity_type="BGV_CASE",
            entity_id=row.id,
            action="CREATED",
            to_status=row.overall_status,
        )
        return Response(_case_payload(row), status=201)
