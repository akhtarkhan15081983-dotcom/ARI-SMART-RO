import hashlib
import json
from collections import Counter

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.access import HasRequiredFeature, has_feature_access, request_company

from . import hr_lifecycle as legacy_lifecycle
from .hr_lifecycle_models import EmployeeHrLifecycle, EmployeeHrLifecycleEvent
from .hr_phase1 import EmployeeDigitalHrFileAPIView as Phase1EmployeeDigitalHrFileAPIView
from .hr_phase2_ats_models import HrLetter
from .hr_phase2_letters_bgv_models import (
    LETTER_TYPES,
    BackgroundVerificationCase,
    BackgroundVerificationCheck,
    BgvPolicy,
    CorporateHrAuditEvent,
    HrLetterAcknowledgement,
    HrLetterTemplate,
    HrLetterWorkflow,
)
from .hr_phase2_recruitment_models import Candidate, CandidateApplication
from .models import EmployeeCareerMovement, EmployeeProfile

LETTER_TYPE_KEYS = {value for value, _ in LETTER_TYPES}
BGV_CHECK_TYPES = {value for value, _ in BackgroundVerificationCheck.TYPE_CHOICES}
BGV_CHECK_STATUSES = {value for value, _ in BackgroundVerificationCheck.STATUS_CHOICES}
BGV_DECISIONS = {"CLEAR", "CONDITIONAL", "FAILED", "WAIVED"}
DEFAULT_REQUIRED_BGV = ["IDENTITY", "ADDRESS", "EDUCATION", "EMPLOYMENT", "CRIMINAL_POLICE", "REFERENCE"]


def _audit(request, *, company, entity_type, entity_id, action, from_status="", to_status="", reason="", metadata=None):
    CorporateHrAuditEvent.objects.create(
        company=company,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        from_status=from_status,
        to_status=to_status,
        reason=reason,
        metadata=metadata or {},
        performed_by=request.user,
    )


def _employee(company, employee_id):
    return EmployeeProfile.objects.filter(company=company, pk=employee_id).select_related("user", "company").first()


def _actor(user):
    return user.get_full_name() or user.phone


def _template_payload(row):
    return {
        "id": row.id,
        "name": row.name,
        "letter_type": row.letter_type,
        "subject": row.subject_template,
        "body": row.body_template,
        "version": row.version,
        "is_active": row.is_active,
        "updated_at": row.updated_at,
        "updated_by": _actor(row.updated_by),
    }


def _letter_payload(row):
    ack = getattr(row, "acknowledgement", None)
    return {
        "id": row.id,
        "letter_type": row.letter_type,
        "subject": row.subject,
        "version": row.version,
        "issued_at": row.issued_at,
        "issued_by": _actor(row.issued_by),
        "acknowledgement_status": row.acknowledgement_status,
        "acknowledged_at": row.acknowledged_at,
        "content_hash": row.content_hash,
        "snapshot": row.snapshot,
        "response_note": ack.note if ack else "",
        "response_evidence": ack.evidence if ack else {},
    }


def _render(template, values):
    result = str(template or "")
    for key, value in values.items():
        result = result.replace("{{" + key + "}}", str(value if value is not None else ""))
    return result


def _letter_context(employee, workflow, request):
    lifecycle = EmployeeHrLifecycle.objects.get(employee=employee)
    company = employee.company
    values = {
        "employee_name": employee.user.get_full_name() or employee.user.phone,
        "employee_id": employee.employee_id,
        "designation": employee.designation,
        "job_title": employee.job_title,
        "department": employee.department,
        "joining_date": employee.joining_date.isoformat() if employee.joining_date else "",
        "work_location": lifecycle.work_location,
        "compensation": str(employee.salary),
        "effective_date": workflow.effective_date.isoformat(),
        "company_name": company.name,
        "issuer": _actor(request.user),
        "letter_type": workflow.letter_type,
        "template_version": workflow.template.version,
    }
    values.update({str(k): v for k, v in (workflow.context or {}).items()})
    return values


def _validate_letter_link(employee, workflow):
    lifecycle = EmployeeHrLifecycle.objects.get(employee=employee)
    kind = workflow.letter_type
    if kind == "CONFIRMATION":
        if lifecycle.employment_status != "CONFIRMED":
            return "Employee must be confirmed before issuing a confirmation letter."
    if kind in {"PROMOTION", "INCREMENT", "TRANSFER"}:
        if not workflow.career_movement_id:
            return "Approved career movement reference is required for this letter type."
        movement = EmployeeCareerMovement.objects.filter(
            pk=workflow.career_movement_id, employee=employee, status="APPROVED"
        ).first()
        if movement is None:
            return "Approved career movement was not found for this employee."
        allowed = {
            "PROMOTION": {"PROMOTION", "DESIGNATION_CHANGE"},
            "INCREMENT": {"SALARY_REVISION"},
            "TRANSFER": {"TRANSFER"},
        }[kind]
        if movement.movement_type not in allowed:
            return "Career movement type does not match the requested letter."
    if kind in {"SEPARATION", "EXPERIENCE"} and lifecycle.employment_status != "SEPARATED":
        return "Employee must be separated before this letter can be issued."
    return ""


def _mask_identity_details(details):
    source = details if isinstance(details, dict) else {}
    blocked = {"aadhaar", "aadhaar_number", "pan", "pan_number", "raw_aadhaar", "raw_pan"}
    return {str(k): v for k, v in source.items() if str(k).lower() not in blocked}


def _check_payload(row):
    details = _mask_identity_details(row.details) if row.check_type == "IDENTITY" else row.details
    return {
        "id": row.id,
        "check_type": row.check_type,
        "status": row.status,
        "details": details,
        "evidence_reference": row.evidence_reference,
        "notes": row.notes,
        "verifier": _actor(row.verifier) if row.verifier else "",
        "verified_at": row.verified_at,
        "updated_at": row.updated_at,
    }


def _case_payload(row):
    return {
        "id": row.id,
        "candidate_id": row.candidate_id,
        "candidate_name": row.candidate.full_name if row.candidate else "",
        "application_id": row.application_id,
        "employee_id": row.employee_id,
        "employee_code": row.employee.employee_id if row.employee else "",
        "employee_name": (row.employee.user.get_full_name() or row.employee.user.phone) if row.employee else "",
        "overall_status": row.overall_status,
        "decision_note": row.decision_note,
        "waiver_reason": row.waiver_reason,
        "decided_by": _actor(row.decided_by) if row.decided_by else "",
        "decided_at": row.decided_at,
        "checks": [_check_payload(check) for check in row.checks.all()],
        "updated_at": row.updated_at,
    }


class HrLettersDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_letters_view"

    def get(self, request):
        company = request_company(request)
        if company is None:
            return Response({"detail": "Active company workspace is required."}, status=403)
        flows = HrLetterWorkflow.objects.filter(company=company)
        letters = HrLetter.objects.filter(company=company, candidate_offer__isnull=True)
        bgv = BackgroundVerificationCase.objects.filter(company=company)
        return Response({
            "letters": {
                "templates_active": HrLetterTemplate.objects.filter(company=company, is_active=True).count(),
                "draft": flows.filter(status="DRAFT").count(),
                "pending_approval": flows.filter(status="PENDING_APPROVAL").count(),
                "approved": flows.filter(status="APPROVED").count(),
                "issued": letters.count(),
                "ack_pending": letters.filter(acknowledgement_status="PENDING").count(),
            },
            "bgv": dict(Counter(bgv.values_list("overall_status", flat=True))),
        })


class HrLetterTemplateAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_letters_view"

    def get(self, request):
        company = request_company(request)
        rows = HrLetterTemplate.objects.filter(company=company)
        letter_type = str(request.query_params.get("letter_type") or "").upper()
        if letter_type:
            rows = rows.filter(letter_type=letter_type)
        return Response({"templates": [_template_payload(row) for row in rows[:500]]})

    @transaction.atomic
    def post(self, request):
        if not has_feature_access(request, "hrms_letters_manage"):
            return Response({"detail": "HR letter management permission is required."}, status=403)
        company = request_company(request)
        name = str(request.data.get("name") or "").strip()
        letter_type = str(request.data.get("letter_type") or "").upper()
        subject = str(request.data.get("subject") or "").strip()
        body = str(request.data.get("body") or "").strip()
        if not name or letter_type not in LETTER_TYPE_KEYS or not subject or not body:
            return Response({"detail": "Name, valid letter type, subject and body are required."}, status=400)
        latest = HrLetterTemplate.objects.filter(company=company, name=name).aggregate(value=Max("version"))["value"] or 0
        row = HrLetterTemplate.objects.create(
            company=company,
            name=name[:160],
            letter_type=letter_type,
            subject_template=subject[:200],
            body_template=body,
            version=latest + 1,
            is_active=bool(request.data.get("is_active", True)),
            created_by=request.user,
            updated_by=request.user,
        )
        _audit(request, company=company, entity_type="HR_LETTER_TEMPLATE", entity_id=row.id, action="CREATED", to_status="ACTIVE" if row.is_active else "INACTIVE", metadata={"version": row.version})
        return Response(_template_payload(row), status=201)


class HrLetterTemplateActionAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_letters_manage"

    @transaction.atomic
    def post(self, request, template_id):
        company = request_company(request)
        row = HrLetterTemplate.objects.select_for_update().filter(company=company, pk=template_id).first()
        if row is None:
            return Response({"detail": "Template not found."}, status=404)
        action = str(request.data.get("action") or "").upper()
        if action not in {"ACTIVATE", "DEACTIVATE"}:
            return Response({"detail": "Action must be ACTIVATE or DEACTIVATE. Create a new version to change content."}, status=400)
        row.is_active = action == "ACTIVATE"
        row.updated_by = request.user
        row.save(update_fields=["is_active", "updated_by", "updated_at"])
        _audit(request, company=company, entity_type="HR_LETTER_TEMPLATE", entity_id=row.id, action=action, to_status="ACTIVE" if row.is_active else "INACTIVE")
        return Response(_template_payload(row))


class HrLetterWorkflowAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_letters_view"

    def get(self, request):
        company = request_company(request)
        rows = HrLetterWorkflow.objects.filter(company=company).select_related("employee__user", "template", "issued_letter")
        status_value = str(request.query_params.get("status") or "").upper()
        if status_value:
            rows = rows.filter(status=status_value)
        return Response({"workflows": [{
            "id": row.id,
            "employee_id": row.employee_id,
            "employee_code": row.employee.employee_id,
            "employee_name": row.employee.user.get_full_name() or row.employee.user.phone,
            "letter_type": row.letter_type,
            "subject": row.subject,
            "effective_date": row.effective_date,
            "status": row.status,
            "template_id": row.template_id,
            "template_version": row.template.version,
            "issued_letter_id": row.issued_letter_id,
            "updated_at": row.updated_at,
        } for row in rows[:1000]]})

    @transaction.atomic
    def post(self, request):
        if not has_feature_access(request, "hrms_letters_manage"):
            return Response({"detail": "HR letter management permission is required."}, status=403)
        company = request_company(request)
        employee = _employee(company, request.data.get("employee_id"))
        template = HrLetterTemplate.objects.filter(company=company, pk=request.data.get("template_id"), is_active=True).first()
        if employee is None or template is None:
            return Response({"detail": "Active employee and template from this company are required."}, status=404)
        try:
            effective_date = parse_date(str(request.data.get("effective_date") or ""))
        except (TypeError, ValueError):
            effective_date = None
        if effective_date is None:
            return Response({"detail": "Valid effective_date is required."}, status=400)
        context = request.data.get("context") or {}
        if not isinstance(context, dict):
            return Response({"detail": "Letter context must be an object."}, status=400)
        draft = HrLetterWorkflow(
            company=company,
            employee=employee,
            template=template,
            letter_type=template.letter_type,
            effective_date=effective_date,
            context=context,
            lifecycle_event_id=request.data.get("lifecycle_event_id") or None,
            career_movement_id=request.data.get("career_movement_id") or None,
            created_by=request.user,
        )
        values = _letter_context(employee, draft, request)
        draft.subject = _render(template.subject_template, values)[:200]
        draft.body = _render(template.body_template, values)
        draft.save()
        _audit(request, company=company, entity_type="HR_LETTER_WORKFLOW", entity_id=draft.id, action="CREATED", to_status=draft.status)
        return Response({"id": draft.id, "status": draft.status}, status=201)


class HrLetterWorkflowActionAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_letters_view"

    @transaction.atomic
    def post(self, request, workflow_id):
        company = request_company(request)
        row = HrLetterWorkflow.objects.select_for_update().filter(company=company, pk=workflow_id).select_related("employee__user", "employee__company", "template", "issued_letter").first()
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
            if not has_feature_access(request, "hrms_letters_manage") or row.status != "APPROVED":
                return Response({"detail": "Only an approved letter can be issued by HR letter management."}, status=400)
            validation_error = _validate_letter_link(row.employee, row)
            if validation_error:
                return Response({"detail": validation_error}, status=409)
            if row.issued_letter_id:
                return Response({"id": row.issued_letter_id, "status": "ISSUED", "idempotent": True})
            version = (HrLetter.objects.filter(employee=row.employee, letter_type=row.letter_type).aggregate(value=Max("version"))["value"] or 0) + 1
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
                "company": {"id": row.company_id, "name": row.company.name},
                "letter_type": row.letter_type,
                "effective_date": row.effective_date.isoformat(),
                "template": {"id": row.template_id, "name": row.template.name, "version": row.template.version},
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
                company=row.company,
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
        _audit(request, company=company, entity_type="HR_LETTER_WORKFLOW", entity_id=row.id, action=action, from_status=before, to_status=row.status, reason=reason, metadata={"issued_letter_id": row.issued_letter_id})
        payload = {"id": row.id, "status": row.status, "issued_letter_id": row.issued_letter_id}
        if row.issued_letter_id:
            payload["content_hash"] = row.issued_letter.content_hash
        return Response(payload)


class IssuedHrLetterAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_letters_view"

    def get(self, request):
        company = request_company(request)
        rows = HrLetter.objects.filter(company=company, employee__isnull=False).select_related("employee__user", "issued_by")
        employee_id = request.query_params.get("employee_id")
        if employee_id:
            rows = rows.filter(employee_id=employee_id)
        return Response({"letters": [{**_letter_payload(row), "employee_id": row.employee_id, "employee_code": row.employee.employee_id, "employee_name": row.employee.user.get_full_name() or row.employee.user.phone} for row in rows[:1000]]})


class HrLetterAcknowledgementAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    @transaction.atomic
    def post(self, request, letter_id):
        company = request_company(request)
        row = HrLetter.objects.select_for_update().filter(company=company, pk=letter_id, employee__isnull=False).select_related("employee__user").first()
        if row is None:
            return Response({"detail": "Issued HR letter not found."}, status=404)
        own_letter = row.employee.user_id == request.user.id
        can_manage = has_feature_access(request, "hrms_letters_manage")
        if not own_letter and not can_manage:
            return Response({"detail": "Only the employee or authorized HR can record this response."}, status=403)
        status_value = str(request.data.get("status") or "").upper()
        if status_value not in {"ACKNOWLEDGED", "DECLINED"}:
            return Response({"detail": "Status must be ACKNOWLEDGED or DECLINED."}, status=400)
        if HrLetterAcknowledgement.objects.filter(letter=row).exists() or row.acknowledgement_status != "PENDING":
            return Response({"detail": "A final acknowledgement response is already recorded."}, status=409)
        evidence = request.data.get("evidence") or {}
        if not isinstance(evidence, dict):
            evidence = {"reference": str(evidence)[:500]}
        ack = HrLetterAcknowledgement.objects.create(
            letter=row,
            status=status_value,
            actor=request.user,
            note=str(request.data.get("note") or "").strip(),
            evidence=evidence,
        )
        row.acknowledgement_status = status_value
        row.acknowledged_at = ack.responded_at
        row.save(update_fields=["acknowledgement_status", "acknowledged_at"])
        _audit(request, company=company, entity_type="HR_LETTER", entity_id=row.id, action=status_value, from_status="PENDING", to_status=status_value)
        return Response(_letter_payload(row))


class BgvPolicyAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_bgv_view"

    def get(self, request):
        company = request_company(request)
        row = BgvPolicy.objects.filter(company=company).first()
        return Response({
            "mandatory_before_ready": row.mandatory_before_ready if row else False,
            "required_checks": row.required_checks if row else [],
        })

    @transaction.atomic
    def patch(self, request):
        if not has_feature_access(request, "hrms_bgv_override"):
            return Response({"detail": "BGV override/policy permission is required."}, status=403)
        company = request_company(request)
        mandatory = bool(request.data.get("mandatory_before_ready"))
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
        _audit(request, company=company, entity_type="BGV_POLICY", entity_id=row.id, action="UPDATED", from_status=str(before), to_status=str(mandatory), metadata={"required_checks": row.required_checks})
        return Response({"mandatory_before_ready": mandatory, "required_checks": row.required_checks})


class BackgroundVerificationCaseAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_bgv_view"

    def get(self, request):
        company = request_company(request)
        rows = BackgroundVerificationCase.objects.filter(company=company).select_related("candidate", "application", "employee__user", "decided_by").prefetch_related("checks__verifier")
        employee_id = request.query_params.get("employee_id")
        application_id = request.query_params.get("application_id")
        if employee_id:
            rows = rows.filter(employee_id=employee_id)
        if application_id:
            rows = rows.filter(application_id=application_id)
        return Response({"cases": [_case_payload(row) for row in rows[:1000]]})

    @transaction.atomic
    def post(self, request):
        if not has_feature_access(request, "hrms_bgv_manage"):
            return Response({"detail": "BGV management permission is required."}, status=403)
        company = request_company(request)
        application = None
        employee = None
        candidate = None
        if request.data.get("application_id"):
            application = CandidateApplication.objects.filter(company=company, pk=request.data.get("application_id")).select_related("candidate").first()
            if application is None:
                return Response({"detail": "Candidate application not found in this company."}, status=404)
            candidate = application.candidate
            employee = application.converted_employee
        elif request.data.get("employee_id"):
            employee = _employee(company, request.data.get("employee_id"))
            if employee is None:
                return Response({"detail": "Employee not found in this company."}, status=404)
            source_application = getattr(employee, "source_candidate_application", None)
            if source_application:
                application = source_application
                candidate = source_application.candidate
        else:
            return Response({"detail": "application_id or employee_id is required."}, status=400)
        existing = BackgroundVerificationCase.objects.filter(company=company).filter(
            transaction.models.Q(application=application) if application else transaction.models.Q(employee=employee)
        ).first()
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
        _audit(request, company=company, entity_type="BGV_CASE", entity_id=row.id, action="CREATED", to_status=row.overall_status)
        return Response(_case_payload(row), status=201)


class BackgroundVerificationCheckAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_bgv_manage"

    @transaction.atomic
    def post(self, request, case_id):
        company = request_company(request)
        case = BackgroundVerificationCase.objects.select_for_update().filter(company=company, pk=case_id).first()
        if case is None:
            return Response({"detail": "BGV case not found."}, status=404)
        check_type = str(request.data.get("check_type") or "").upper()
        status_value = str(request.data.get("status") or "PENDING").upper()
        if check_type not in BGV_CHECK_TYPES or status_value not in BGV_CHECK_STATUSES:
            return Response({"detail": "Valid BGV check type and status are required."}, status=400)
        details = request.data.get("details") or {}
        if not isinstance(details, dict):
            return Response({"detail": "BGV details must be an object."}, status=400)
        if check_type == "IDENTITY":
            details = _mask_identity_details(details)
        row, created = BackgroundVerificationCheck.objects.get_or_create(
            case=case,
            check_type=check_type,
            defaults={"status": status_value},
        )
        before = row.status
        row.status = status_value
        row.details = details
        row.evidence_reference = str(request.data.get("evidence_reference") or "").strip()[:300]
        row.notes = str(request.data.get("notes") or "").strip()
        row.verifier = request.user
        row.verified_at = timezone.now() if status_value in {"VERIFIED", "FAILED", "NOT_APPLICABLE"} else None
        row.save()
        if case.overall_status == "NOT_STARTED":
            case.overall_status = "IN_PROGRESS"
            case.save(update_fields=["overall_status", "updated_at"])
        _audit(request, company=company, entity_type="BGV_CHECK", entity_id=row.id, action="CREATED" if created else "UPDATED", from_status=before, to_status=row.status, metadata={"case_id": case.id, "check_type": check_type})
        return Response(_check_payload(row), status=201 if created else 200)


class BackgroundVerificationDecisionAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_bgv_view"

    @transaction.atomic
    def post(self, request, case_id):
        company = request_company(request)
        case = BackgroundVerificationCase.objects.select_for_update().filter(company=company, pk=case_id).prefetch_related("checks").first()
        if case is None:
            return Response({"detail": "BGV case not found."}, status=404)
        decision = str(request.data.get("decision") or "").upper()
        note = str(request.data.get("reason") or request.data.get("note") or "").strip()
        if decision not in BGV_DECISIONS:
            return Response({"detail": "Decision must be CLEAR, CONDITIONAL, FAILED or WAIVED."}, status=400)
        if decision == "WAIVED":
            if not has_feature_access(request, "hrms_bgv_override"):
                return Response({"detail": "BGV override permission is required for waiver."}, status=403)
            if not note:
                return Response({"detail": "Waiver reason is required."}, status=400)
        elif not has_feature_access(request, "hrms_bgv_decide"):
            return Response({"detail": "BGV final decision permission is required."}, status=403)
        if decision == "CLEAR":
            policy = BgvPolicy.objects.filter(company=company).first()
            required = set(policy.required_checks if policy and policy.required_checks else [])
            statuses = {row.check_type: row.status for row in case.checks.all()}
            missing = sorted(kind for kind in required if statuses.get(kind) not in {"VERIFIED", "NOT_APPLICABLE"})
            if missing:
                return Response({"detail": "Required BGV checks are not satisfactorily closed.", "pending_checks": missing}, status=409)
        before = case.overall_status
        case.overall_status = decision
        case.decision_note = note
        case.waiver_reason = note if decision == "WAIVED" else ""
        case.decided_by = request.user
        case.decided_at = timezone.now()
        case.save()
        _audit(request, company=company, entity_type="BGV_CASE", entity_id=case.id, action="FINAL_DECISION", from_status=before, to_status=decision, reason=note)
        return Response(_case_payload(case))


class EmployeeDigitalHrFileWithLettersAPIView(Phase1EmployeeDigitalHrFileAPIView):
    def get(self, request, employee_id):
        response = super().get(request, employee_id)
        if response.status_code != 200:
            return response
        company = request_company(request)
        employee = _employee(company, employee_id)
        if employee is None:
            return Response({"detail": "Employee not found."}, status=404)
        rows = HrLetter.objects.filter(company=company, employee=employee).select_related("issued_by")
        response.data["hr_letters"] = [_letter_payload(row) for row in rows]
        bgv = BackgroundVerificationCase.objects.filter(company=company, employee=employee).prefetch_related("checks__verifier").first()
        response.data["background_verification"] = _case_payload(bgv) if bgv else None
        return response


# Add the optional BGV gate to the existing readiness engine without changing
# the default behavior for companies that have not enabled the policy.
_base_readiness = legacy_lifecycle._readiness


def _bgv_aware_readiness(employee, lifecycle):
    before_status = lifecycle.employment_status
    result = _base_readiness(employee, lifecycle)
    policy = BgvPolicy.objects.filter(company=employee.company, mandatory_before_ready=True).first()
    if policy is None:
        result["checks"]["bgv"] = True
        result["bgv"] = {"required": False, "status": "OPTIONAL"}
        return result
    case = BackgroundVerificationCase.objects.filter(company=employee.company, employee=employee).first()
    bgv_ok = bool(case and case.overall_status in {"CLEAR", "WAIVED"})
    result["checks"]["bgv"] = bgv_ok
    result["bgv"] = {"required": True, "status": case.overall_status if case else "NOT_STARTED"}
    if bgv_ok or lifecycle.hr_override_ready:
        return result
    result["ready_without_override"] = False
    result["ready"] = False
    result["stage"] = "HR_REVIEW"
    update_fields = []
    if lifecycle.hr_stage != "HR_REVIEW":
        lifecycle.hr_stage = "HR_REVIEW"
        update_fields.append("hr_stage")
    if before_status == "ONBOARDING" and lifecycle.employment_status != "ONBOARDING":
        lifecycle.employment_status = "ONBOARDING"
        update_fields.append("employment_status")
    if update_fields:
        lifecycle.save(update_fields=[*update_fields, "updated_at"])
    return result


legacy_lifecycle._readiness = _bgv_aware_readiness
