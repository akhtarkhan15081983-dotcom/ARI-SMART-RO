from calendar import monthrange
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.access import HasRequiredFeature, has_feature_access, request_company
from .models import EmployeeProfile, EmployeeCareerMovement
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
        "designation": employee.designation, "job_title": employee.job_title,
        "department": employee.department, "grade": employee.grade,
        "salary": str(employee.salary), "reporting_manager_id": employee.reporting_manager_id,
        "work_location": lifecycle.work_location,
        "compensation_profile": lifecycle.compensation_profile,
        "employment_type": lifecycle.employment_type,
        "employment_status": lifecycle.employment_status, "hr_stage": lifecycle.hr_stage,
        "probation_months": lifecycle.probation_months,
        "probation_start_date": lifecycle.probation_start_date.isoformat() if lifecycle.probation_start_date else None,
        "confirmation_due_date": lifecycle.confirmation_due_date.isoformat() if lifecycle.confirmation_due_date else None,
        "confirmed_at": lifecycle.confirmed_at.isoformat() if lifecycle.confirmed_at else None,
    }


def _audit(action, actor, verb, old, new, reason="", metadata=None):
    EmployeeLifecycleAudit.objects.create(company=action.company, employee=action.employee, entity_type="LIFECYCLE_ACTION", entity_id=action.id, action=verb, from_status=old, to_status=new, reason=reason or "", metadata=metadata or {}, performed_by=actor)


def _payload(row):
    return {"id": row.id, "employee_id": row.employee_id, "action_type": row.action_type, "effective_date": row.effective_date, "status": row.status, "reason": row.reason, "proposed_changes": row.proposed_changes, "manager_assessment": row.manager_assessment, "hr_assessment": row.hr_assessment, "career_movement_id": row.career_movement_id, "letter_workflow_id": row.letter_workflow_id}


def _validate_change(company, employee, action_type, proposed):
    if action_type in {"PROMOTION", "TRANSFER"} and proposed.get("reporting_manager_id"):
        manager = EmployeeProfile.objects.filter(company=company, id=proposed["reporting_manager_id"], is_active=True).first()
        if not manager or manager.id == employee.id:
            return "Reporting manager must be another active employee in the same company."
    if action_type == "INCREMENT":
        try:
            salary = Decimal(str(proposed.get("salary", "")))
        except (InvalidOperation, TypeError):
            return "A valid proposed salary is required."
        if salary < 0:
            return "Proposed salary cannot be negative."
    return None


def _create_letter(action, event, movement, actor):
    letter_type = {"CONFIRMATION": "CONFIRMATION", "PROMOTION": "PROMOTION", "INCREMENT": "INCREMENT", "TRANSFER": "TRANSFER"}.get(action.action_type)
    if not letter_type:
        return None
    template = HrLetterTemplate.objects.filter(company=action.company, letter_type=letter_type, is_active=True).order_by("-version").first()
    if not template:
        return None
    flow = HrLetterWorkflow.objects.create(company=action.company, employee=action.employee, template=template, letter_type=letter_type, subject=template.subject_template, body=template.body_template, effective_date=action.effective_date, context={"lifecycle_action_id": action.id, "snapshot_before": action.snapshot_before, "proposed_changes": action.proposed_changes}, lifecycle_event_id=event.id if event else None, career_movement_id=movement.id if movement else None, created_by=actor)
    return flow


def _apply_career_action(row, lifecycle, actor):
    employee = EmployeeProfile.objects.select_for_update().get(id=row.employee_id, company=row.company)
    proposed = row.proposed_changes or {}
    error = _validate_change(row.company, employee, row.action_type, proposed)
    if error:
        raise ValueError(error)
    movement_type = {"PROMOTION": "PROMOTION", "INCREMENT": "SALARY_REVISION", "TRANSFER": "TRANSFER"}[row.action_type]
    manager = None
    if proposed.get("reporting_manager_id"):
        manager = EmployeeProfile.objects.get(company=row.company, id=proposed["reporting_manager_id"])
    movement = EmployeeCareerMovement.objects.create(
        employee=employee, movement_type=movement_type, effective_date=row.effective_date,
        old_designation=employee.designation, new_designation=str(proposed.get("designation", employee.designation)),
        old_job_title=employee.job_title, new_job_title=str(proposed.get("job_title", employee.job_title)),
        old_department=employee.department, new_department=str(proposed.get("department", employee.department)),
        old_grade=employee.grade, new_grade=str(proposed.get("grade", employee.grade)),
        old_salary=employee.salary, new_salary=Decimal(str(proposed.get("salary", employee.salary))),
        old_reporting_manager=employee.reporting_manager, new_reporting_manager=manager if "reporting_manager_id" in proposed else employee.reporting_manager,
        reason=row.reason, status="APPROVED", created_by=row.created_by, approved_by=row.approved_by, approved_at=row.approved_at,
    )
    if row.action_type == "PROMOTION":
        employee.designation = movement.new_designation; employee.job_title = movement.new_job_title; employee.department = movement.new_department; employee.grade = movement.new_grade
    elif row.action_type == "INCREMENT":
        employee.salary = movement.new_salary
        history = list(lifecycle.compensation_profile.get("history", [])) if isinstance(lifecycle.compensation_profile, dict) else []
        history.append({"effective_date": row.effective_date.isoformat(), "old_salary": str(movement.old_salary), "new_salary": str(movement.new_salary), "lifecycle_action_id": row.id})
        lifecycle.compensation_profile = {**(lifecycle.compensation_profile if isinstance(lifecycle.compensation_profile, dict) else {}), "current_salary": str(movement.new_salary), "history": history}
    elif row.action_type == "TRANSFER":
        employee.department = movement.new_department; employee.reporting_manager = movement.new_reporting_manager
        if "work_location" in proposed: lifecycle.work_location = str(proposed.get("work_location") or "")
    employee.save(); lifecycle.save()
    return movement


class EmployeeLifecycleActionListAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_lifecycle_view"

    def get(self, request):
        company = request_company(request)
        if not company: return Response({"detail": "Active company required."}, status=403)
        qs = EmployeeLifecycleAction.objects.filter(company=company).select_related("employee")
        if request.query_params.get("employee_id"): qs = qs.filter(employee_id=request.query_params["employee_id"])
        if request.query_params.get("action_type"): qs = qs.filter(action_type=request.query_params["action_type"].upper())
        if request.query_params.get("status"): qs = qs.filter(status=request.query_params["status"].upper())
        return Response([_payload(row) for row in qs[:500]])

    def post(self, request):
        if not has_feature_access(request, "hrms_lifecycle_manage"): return Response({"detail": "Lifecycle manage permission required."}, status=403)
        company = request_company(request); employee = _employee(company, request.data.get("employee_id")) if company else None
        if not employee: return Response({"detail": "Employee not found in active company."}, status=404)
        action_type = str(request.data.get("action_type", "")).upper()
        allowed = {"PROBATION_REVIEW", "PROBATION_EXTENSION", "CONFIRMATION", "PROMOTION", "INCREMENT", "TRANSFER"}
        if action_type not in allowed: return Response({"detail": "Unsupported lifecycle action type."}, status=400)
        reason = str(request.data.get("reason", "")).strip(); proposed = request.data.get("proposed_changes") or {}
        if action_type in {"PROBATION_EXTENSION", "PROMOTION", "INCREMENT", "TRANSFER"} and not reason: return Response({"detail": "A reason is required for this lifecycle action."}, status=400)
        effective_date = parse_date(str(request.data.get("effective_date", ""))) or timezone.localdate()
        lifecycle, _ = EmployeeHrLifecycle.objects.get_or_create(employee=employee)
        if action_type == "PROBATION_EXTENSION":
            try: months = int(proposed.get("extension_months") or 0)
            except (TypeError, ValueError): months = 0
            if months < 1 or months > 24: return Response({"detail": "extension_months must be between 1 and 24."}, status=400)
        error = _validate_change(company, employee, action_type, proposed)
        if error: return Response({"detail": error}, status=400)
        row = EmployeeLifecycleAction.objects.create(company=company, employee=employee, action_type=action_type, effective_date=effective_date, reason=reason, proposed_changes=proposed, snapshot_before=_snapshot(employee, lifecycle), created_by=request.user)
        _audit(row, request.user, "CREATE", "", "DRAFT", reason)
        return Response(_payload(row), status=status.HTTP_201_CREATED)


class EmployeeLifecycleActionWorkflowAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, action_id):
        company = request_company(request)
        row = EmployeeLifecycleAction.objects.select_for_update().select_related("employee", "employee__user", "employee__reporting_manager").filter(company=company, id=action_id).first()
        if not row: return Response({"detail": "Lifecycle action not found."}, status=404)
        verb = str(request.data.get("action", "")).upper(); reason = str(request.data.get("reason", "")).strip(); old = row.status
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
            lifecycle = EmployeeHrLifecycle.objects.select_for_update().get(employee=row.employee); before_status = lifecycle.employment_status; movement = None
            try:
                if row.action_type == "PROBATION_EXTENSION":
                    months = int(row.proposed_changes.get("extension_months") or 0)
                    if months < 1 or not row.reason.strip(): return Response({"detail": "Valid extension months and reason required."}, status=400)
                    lifecycle.confirmation_due_date = _add_months(lifecycle.confirmation_due_date or row.effective_date, months); lifecycle.probation_months += months; lifecycle.employment_type = "PROBATION"; lifecycle.employment_status = "PROBATION"; lifecycle.save()
                elif row.action_type == "CONFIRMATION":
                    lifecycle.employment_type = "PERMANENT"; lifecycle.employment_status = "CONFIRMED"; lifecycle.confirmed_at = row.effective_date; lifecycle.save()
                elif row.action_type in {"PROMOTION", "INCREMENT", "TRANSFER"}:
                    movement = _apply_career_action(row, lifecycle, request.user); row.career_movement_id = movement.id
                else:
                    lifecycle.manager_review_status = "COMPLETED"; lifecycle.hr_review_status = "COMPLETED"; lifecycle.save()
            except (ValueError, InvalidOperation) as exc:
                return Response({"detail": str(exc)}, status=400)
            lifecycle.refresh_from_db(); lifecycle.manager_review_note = str(row.manager_assessment.get("note", "")); lifecycle.hr_review_note = str(row.hr_assessment.get("note", "")); lifecycle.save()
            event = EmployeeHrLifecycleEvent.objects.create(employee=row.employee, event_type=row.action_type, effective_date=row.effective_date, from_status=before_status, to_status=lifecycle.employment_status, note=row.reason, metadata={"lifecycle_action_id": row.id, "snapshot_before": row.snapshot_before, "career_movement_id": movement.id if movement else None}, created_by=request.user)
            flow = _create_letter(row, event, movement, request.user)
            if flow: row.letter_workflow_id = flow.id
            row.status = "APPLIED"; row.applied_at = timezone.now()
        else: return Response({"detail": "Unsupported action."}, status=400)
        row.save(); _audit(row, request.user, verb, old, row.status, reason, {"manager_assessment": row.manager_assessment, "hr_assessment": row.hr_assessment, "career_movement_id": row.career_movement_id})
        return Response(_payload(row))


class EmployeeLifecycleProbationQueueAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_lifecycle_view"
    def get(self, request):
        company = request_company(request); today = timezone.localdate(); lifecycles = EmployeeHrLifecycle.objects.filter(employee__company=company, employment_type="PROBATION").select_related("employee"); due = []
        for life in lifecycles:
            if life.confirmation_due_date: due.append({"employee_id": life.employee_id, "employee_code": life.employee.employee_id, "confirmation_due_date": life.confirmation_due_date, "overdue": life.confirmation_due_date < today, "days_to_due": (life.confirmation_due_date - today).days})
        due.sort(key=lambda item: item["confirmation_due_date"]); return Response({"count": len(due), "items": due})
