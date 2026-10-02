import hashlib
import json

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.response import Response

from tenancy.access import has_feature_access, request_company

from .hr_phase2_ats_models import HrLetter
from .hr_phase2_letters_bgv import (
    DEFAULT_REQUIRED_BGV,
    BGV_CHECK_TYPES,
    BackgroundVerificationCaseAPIView as BaseBackgroundVerificationCaseAPIView,
    BgvPolicyAPIView as BaseBgvPolicyAPIView,
    HrLetterWorkflowActionAPIView as BaseHrLetterWorkflowActionAPIView,
    _actor,
    _audit,
    _case_payload,
    _employee,
    _letter_context,
    _validate_letter_link,
)
from .hr_phase2_letters_bgv_models import (
    BackgroundVerificationCase,
    BgvPolicy,
    HrLetterWorkflow,
)
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


class HrLetterWorkflowActionAPIView(BaseHrLetterWorkflowActionAPIView):
    @transaction.atomic
    def post(self, request, workflow_id):
        company = request_company(request)
        if company is None:
            return Response({"detail": "Active company workspace is required."}, status=403)

        # Lock only the workflow row and non-nullable relations. Nullable
        # issued_letter/company joins cannot safely participate in PostgreSQL
        # SELECT ... FOR UPDATE outer joins.
        row = (
            HrLetterWorkflow.objects.select_for_update()
            .filter(company=company, pk=workflow_id)
            .select_related("employee__user", "template")
            .first()
        )
        if row is None:
            return Response({"detail": "Letter workflow not found."}, status=404)

        action = str(request.data.get("action") or "").upper()
        reason = str(request.data.get("reason") or request.data.get("note") or "").strip()
        before = row.status

        if action == "SUBMIT":
            if not has_feature_access(request, "hrms_letters_manage") or row.status != "DRAFT":
                return Response({"detail": "Only a draft can be submitted by HR letter management."}, status=400)
            row.status = "PENDING_APPROVAL"

        elif action == "APPROVE":
            if not has_feature_access(request, "hrms_letters_approve"):
                return Response({"detail": "HR letter approval permission is required."}, status=403)
            if row.status != "PENDING_APPROVAL":
                return Response({"detail": "Only pending letters can be approved."}, status=400)
            row.status = "APPROVED"
            row.approval_note = reason
            row.approved_by = request.user
            row.approved_at = timezone.now()

        elif action == "REJECT":
            if not has_feature_access(request, "hrms_letters_approve"):
                return Response({"detail": "HR letter approval permission is required."}, status=403)
            if row.status != "PENDING_APPROVAL" or not reason:
                return Response({"detail": "Pending letter and rejection reason are required."}, status=400)
            row.status = "REJECTED"
            row.rejection_reason = reason

        elif action == "ISSUE":
            if row.issued_letter_id:
                issued = HrLetter.objects.filter(pk=row.issued_letter_id).first()
                return Response({
                    "id": row.id,
                    "status": "ISSUED",
                    "issued_letter_id": row.issued_letter_id,
                    "content_hash": issued.content_hash if issued else "",
                    "idempotent": True,
                })
            if not has_feature_access(request, "hrms_letters_manage") or row.status != "APPROVED":
                return Response({"detail": "Only an approved letter can be issued by HR letter management."}, status=400)
            validation_error = _validate_letter_link(row.employee, row)
            if validation_error:
                return Response({"detail": validation_error}, status=409)

            version = (
                HrLetter.objects.filter(employee=row.employee, letter_type=row.letter_type)
                .aggregate(value=Max("version"))["value"]
                or 0
            ) + 1
            values = _letter_context(row.employee, row, request)
            snapshot = {
                "employee": {
                    "name": values["employee_name"],
                    "employee_id": row.employee.employee_id,
                    "designation": row.employee.designation,
                    "job_title": row.employee.job_title,
                    "department": row.employee.department,
                    "joining_date": values["joining_date"],
                    "work_location": values["work_location"],
                    "compensation": values["compensation"],
                },
                "company": {"id": row.company_id, "name": company.name},
                "letter_type": row.letter_type,
                "effective_date": row.effective_date.isoformat(),
                "template": {
                    "id": row.template_id,
                    "name": row.template.name,
                    "version": row.template.version,
                },
                "subject": row.subject,
                "body": row.body,
                "issuer": _actor(request.user),
                "context": row.context,
                "lifecycle_event_id": row.lifecycle_event_id,
                "career_movement_id": row.career_movement_id,
            }
            canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            letter = HrLetter.objects.create(
                company=company,
                letter_type=row.letter_type,
                employee=row.employee,
                subject=row.subject,
                snapshot=snapshot,
                content_hash=digest,
                version=version,
                issued_by=request.user,
            )
            row.issued_letter = letter
            row.status = "ISSUED"

        else:
            return Response({"detail": "Unsupported HR letter action."}, status=400)

        row.save()
        _audit(
            request,
            company=company,
            entity_type="HR_LETTER_WORKFLOW",
            entity_id=row.id,
            action=action,
            from_status=before,
            to_status=row.status,
            reason=reason,
            metadata={"issued_letter_id": row.issued_letter_id},
        )
        payload = {
            "id": row.id,
            "status": row.status,
            "issued_letter_id": row.issued_letter_id,
        }
        if row.issued_letter_id:
            payload["content_hash"] = HrLetter.objects.get(pk=row.issued_letter_id).content_hash
        return Response(payload)
