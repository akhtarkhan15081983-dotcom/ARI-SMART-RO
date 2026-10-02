from calendar import monthrange

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.access import HasRequiredFeature, has_feature_access, request_company
from .models import EmployeeProfile
from .hr_lifecycle_models import EmployeeHrLifecycle, EmployeeHrLifecycleEvent
from .hr_phase2_lifecycle_models import EmployeeLifecycleAction, EmployeeLifecycleAudit
from .hr_phase2_letters_bgv_models import HrLetterTemplate, HrLetterWorkflow


def _add_months(value, months):
    total = value.year * 12 + value.month - 1 + months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    return value.replace(year=year, month=month, day=min(value.day, monthrange(year, month)[1]))


def _employee(company, employee_id):
    return EmployeeProfile.objects.select_related("user", "reporting_manager").filter(company=company, id=employee_id).first()


def _snapshot(employee, lifecycle):
    return {
        "employment_type": lifecycle.employment_type,
        "employment_status": lifecycle.employment_status,
        "hr_stage": lifecycle.hr_stage,
        "probation_months": lifecycle.probation_months,
        "probation_start_date": lifecycle.probation_start_date.isoformat() if lifecycle.probation_start_date else None,
        "confirmation_due_date": lifecycle.confirmation_due_date.isoformat() if lifecycle.confirmation_due_date else None,
        "confirmed_at": lifecycle.confirmed_at.isoformat() if lifecycle.confirmed_at else None,
    }


def _audit(action, actor, verb, old, new, reason="", metadata=None):
    EmployeeLifecycleAudit.objects.create(company=action.company, employee=action.employee, entity_type="LIFECYCLE_ACTION", entity_id=action.id, action=verb, from_status=old, to_status=new, reason=reason or "", metadata=metadata or {}, performed_by=actor)


def _payload(row):
    return {"id": row.id, "employee_id": row.employee_id, "action_type": row.action_type, "effective_date": row.effective_date, "status": row.status, "reason": row.reason, "proposed_changes": row.proposed_changes, "manager_assessment": row.manager_assessment, "hr_assessment": row.hr_assessment, "letter_workflow_id": row.letter_workflow_id}


class EmployeeLifecycleActionListAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_lifecycle_view"

    def get(self, request):
        company = request_company(request)
        if not company:
            return Response({"detail": "Active company required."}, status=403)
        qs = EmployeeLifecycleAction.objects.filter(company=company).select_related("employee")
        employee_id = request.query_params.get("employee_id")
        action_type = request.query_params.get("action_type")
        state = request.query_params.get("status")
        if employee_id: qs = qs.filter(employee_id=employee_id)
        if action_type: qs = qs.filter(action_type=action_type.upper())
        if state: qs = qs.filter(status=state.upper())
        return Response([_payload(row) for row in qs[:500]])

    def post(self, request):
        if not has_feature_access(request, "hrms_lifecycle_manage"):
            return Response({"detail": "Lifecycle manage permission required."}, status=403)
        company = request_company(request)
        employee = _employee(company, request.data.get("employee_id")) if company else None
        if not employee:
            return Response({"detail": "Employee not found in active company."}, status=404)
        action_type = str(request.data.get("action_type", "")).upper()
        if action_type not in {"PROBATION_REVIEW", "PROBATION_EXTENSION", "CONFIRMATION"}:
            return Response({"detail": "This endpoint currently accepts probation/confirmation actions."}, status=400)
        reason = str(request.data.get("reason", "")).strip()
        if action_type == "PROBATION_EXTENSION" and not reason:
            return Response({"detail": "Probation extension requires a reason."}, status=400)
        effective_date = parse_date(str(request.data.get("effective_date", ""))) or timezone.localdate()
        lifecycle, _ = EmployeeHrLifecycle.objects.get_or_create(employee=employee)
        proposed = request.data.get("proposed_changes") or {}
        if action_type == "PROBATION_EXTENSION":
            months = int(proposed.get("extension_months") or 0)
            if months < 1 or months > 24:
                return Response({"detail": "extension_months must be between 1 and 24."}, status=400)
        row = EmployeeLifecycleAction.objects.create(company=company, employee=employee, action_type=action_type, effective_date=effective_date, reason=reason, proposed_changes=proposed, snapshot_before=_snapshot(employee, lifecycle), created_by=request.user)
        _audit(row, request.user, "CREATE", "", "DRAFT", reason)
        return Response(_payload(row), status=status.HTTP_201_CREATED)


class EmployeeLifecycleActionWorkflowAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, action_id):
        company = request_company(request)
        row = EmployeeLifecycleAction.objects.select_for_update().select_related("employee", "employee__user", "employee__reporting_manager").filter(company=company, id=action_id).first()
        if not row:
            return Response({"detail": "Lifecycle action not found."}, status=404)
        verb = str(request.data.get("action", "")).upper()
        reason = str(request.data.get("reason", "")).strip()
        old = row.status
        if verb == "SUBMIT_MANAGER":
            if not has_feature_access(request, "hrms_lifecycle_manage") or old != "DRAFT": return Response({"detail": "Invalid transition."}, status=400)
            row.status = "MANAGER_REVIEW"
        elif verb == "MANAGER_REVIEW":
            if not has_feature_access(request, "hrms_lifecycle_manager_review") or old != "MANAGER_REVIEW": return Response({"detail": "Manager review not allowed."}, status=403)
            if row.employee.user_id == request.user.id: return Response({"detail": "Self-review is not allowed."}, status=403)
            assessment = request.data.get("assessment") or {}
            if not assessment: return Response({"detail": "Manager assessment is required."}, status=400)
            row.manager_assessment = assessment; row.manager_reviewed_by = request.user; row.manager_reviewed_at = timezone.now(); row.status = "HR_REVIEW"
        elif verb == "HR_REVIEW":
            if not has_feature_access(request, "hrms_lifecycle_hr_review") or old != "HR_REVIEW": return Response({"detail": "HR review not allowed."}, status=403)
            if request.user.id in {row.created_by_id, row.employee.user_id, row.manager_reviewed_by_id}: return Response({"detail": "Approval segregation prevents this HR review."}, status=403)
            assessment = request.data.get("assessment") or {}
            if not assessment: return Response({"detail": "HR assessment is required."}, status=400)
            row.hr_assessment = assessment; row.hr_reviewed_by = request.user; row.hr_reviewed_at = timezone.now(); row.status = "PENDING_APPROVAL"
        elif verb == "APPROVE":
            if not has_feature_access(request, "hrms_lifecycle_approve") or old != "PENDING_APPROVAL": return Response({"detail": "Approval not allowed."}, status=403)
            if request.user.id in {row.created_by_id, row.employee.user_id, row.manager_reviewed_by_id, row.hr_reviewed_by_id}: return Response({"detail": "Self-approval/approval overlap is not allowed."}, status=403)
            row.approved_by = request.user; row.approved_at = timezone.now(); row.status = "APPROVED"
        elif verb == "REJECT":
            if not has_feature_access(request, "hrms_lifecycle_approve") or old not in {"PENDING_APPROVAL", "APPROVED"}: return Response({"detail": "Rejection not allowed."}, status=403)
            if not reason: return Response({"detail": "Rejection reason is required."}, status=400)
            row.status = "REJECTED"
        elif verb == "APPLY":
            if not has_feature_access(request, "hrms_lifecycle_approve") or old != "APPROVED": return Response({"detail": "Only approved actions can be applied."}, status=403)
            if request.user.id in {row.created_by_id, row.employee.user_id}: return Response({"detail": "Creator/employee cannot apply their own sensitive action."}, status=403)
            lifecycle = EmployeeHrLifecycle.objects.select_for_update().get(employee=row.employee)
            before_status = lifecycle.employment_status
            if row.action_type == "PROBATION_EXTENSION":
                months = int(row.proposed_changes.get("extension_months") or 0)
                if months < 1 or not row.reason.strip(): return Response({"detail": "Valid extension months and reason required."}, status=400)
                base = lifecycle.confirmation_due_date or row.effective_date
                lifecycle.confirmation_due_date = _add_months(base, months); lifecycle.probation_months += months; lifecycle.employment_type = "PROBATION"; lifecycle.employment_status = "PROBATION"
            elif row.action_type == "CONFIRMATION":
                lifecycle.employment_type = "PERMANENT"; lifecycle.employment_status = "CONFIRMED"; lifecycle.confirmed_at = row.effective_date
            else:
                lifecycle.manager_review_status = "COMPLETED"; lifecycle.hr_review_status = "COMPLETED"
            lifecycle.manager_review_note = str(row.manager_assessment.get("note", "")); lifecycle.hr_review_note = str(row.hr_assessment.get("note", "")); lifecycle.save()
            event = EmployeeHrLifecycleEvent.objects.create(employee=row.employee, event_type=row.action_type, effective_date=row.effective_date, from_status=before_status, to_status=lifecycle.employment_status, note=row.reason, metadata={"lifecycle_action_id": row.id, "snapshot_before": row.snapshot_before}, created_by=request.user)
            if row.action_type == "CONFIRMATION":
                template = HrLetterTemplate.objects.filter(company=company, letter_type="CONFIRMATION", is_active=True).order_by("-version").first()
                if template:
                    flow = HrLetterWorkflow.objects.create(company=company, employee=row.employee, template=template, letter_type="CONFIRMATION", subject=template.subject_template, body=template.body_template, effective_date=row.effective_date, context={"lifecycle_action_id": row.id}, lifecycle_event_id=event.id, created_by=request.user)
                    row.letter_workflow_id = flow.id
            row.status = "APPLIED"; row.applied_at = timezone.now()
        else:
            return Response({"detail": "Unsupported action."}, status=400)
        row.save()
        _audit(row, request.user, verb, old, row.status, reason, {"manager_assessment": row.manager_assessment, "hr_assessment": row.hr_assessment})
        return Response(_payload(row))


class EmployeeLifecycleProbationQueueAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_lifecycle_view"

    def get(self, request):
        company = request_company(request)
        today = timezone.localdate()
        lifecycles = EmployeeHrLifecycle.objects.filter(employee__company=company, employment_type="PROBATION").select_related("employee")
        due = []
        for life in lifecycles:
            if life.confirmation_due_date:
                due.append({"employee_id": life.employee_id, "employee_code": life.employee.employee_id, "confirmation_due_date": life.confirmation_due_date, "overdue": life.confirmation_due_date < today, "days_to_due": (life.confirmation_due_date - today).days})
        due.sort(key=lambda item: item["confirmation_due_date"])
        return Response({"count": len(due), "items": due})
