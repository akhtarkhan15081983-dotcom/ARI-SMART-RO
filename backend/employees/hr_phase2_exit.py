from decimal import Decimal, InvalidOperation

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
from .hr_phase2_lifecycle_models import ExitCase, ExitClearance, EmployeeLifecycleAudit
from .hr_phase2_letters_bgv_models import HrLetterTemplate, HrLetterWorkflow


def _audit(case, actor, verb, old, new, reason="", metadata=None):
    EmployeeLifecycleAudit.objects.create(
        company=case.company, employee=case.employee, entity_type="EXIT_CASE",
        entity_id=case.id, action=verb, from_status=old, to_status=new,
        reason=reason or "", metadata=metadata or {}, performed_by=actor,
    )


def _clearance_payload(row):
    return {"id": row.id, "type": row.clearance_type, "status": row.status, "note": row.note, "evidence": row.evidence, "waiver_reason": row.waiver_reason, "reviewed_by_id": row.reviewed_by_id, "reviewed_at": row.reviewed_at}


def _payload(case):
    return {
        "id": case.id, "employee_id": case.employee_id, "separation_type": case.separation_type,
        "resignation_date": case.resignation_date, "notice_days": case.notice_days,
        "proposed_last_working_date": case.proposed_last_working_date,
        "approved_last_working_date": case.approved_last_working_date,
        "notice_waiver_days": case.notice_waiver_days,
        "notice_recovery_amount": str(case.notice_recovery_amount), "reason": case.reason,
        "status": case.status, "final_settlement_ready": case.final_settlement_ready,
        "approved_by_id": case.approved_by_id, "approved_at": case.approved_at,
        "separated_at": case.separated_at,
        "clearances": [_clearance_payload(x) for x in case.clearances.all().order_by("clearance_type")],
    }


def _create_letter(case, letter_type, event, actor):
    template = HrLetterTemplate.objects.filter(company=case.company, letter_type=letter_type, is_active=True).order_by("-version").first()
    if not template:
        return None
    return HrLetterWorkflow.objects.create(
        company=case.company, employee=case.employee, template=template, letter_type=letter_type,
        subject=template.subject_template, body=template.body_template,
        effective_date=case.approved_last_working_date or timezone.localdate(),
        context={"exit_case_id": case.id, "separation_type": case.separation_type, "reason": case.reason},
        lifecycle_event_id=event.id if event else None, created_by=actor,
    )


class ExitCaseAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_lifecycle_view"

    def get(self, request):
        company = request_company(request)
        if not company: return Response({"detail": "Active company required."}, status=403)
        qs = ExitCase.objects.filter(company=company).select_related("employee").prefetch_related("clearances")
        if request.query_params.get("employee_id"): qs = qs.filter(employee_id=request.query_params["employee_id"])
        if request.query_params.get("status"): qs = qs.filter(status=request.query_params["status"].upper())
        return Response([_payload(x) for x in qs.order_by("-created_at")[:500]])

    @transaction.atomic
    def post(self, request):
        if not has_feature_access(request, "hrms_exit_manage"): return Response({"detail": "Exit manage permission required."}, status=403)
        company = request_company(request)
        employee = EmployeeProfile.objects.filter(company=company, id=request.data.get("employee_id")).first()
        if not employee: return Response({"detail": "Employee not found in active company."}, status=404)
        if ExitCase.objects.filter(company=company, employee=employee).exclude(status="CANCELLED").exists(): return Response({"detail": "An active exit case already exists for this employee."}, status=409)
        separation_type = str(request.data.get("separation_type", "")).upper()
        if separation_type not in dict(ExitCase.SEPARATION_TYPES): return Response({"detail": "Invalid separation type."}, status=400)
        reason = str(request.data.get("reason", "")).strip()
        if not reason: return Response({"detail": "Exit reason is required."}, status=400)
        proposed_lwd = parse_date(str(request.data.get("proposed_last_working_date", "")))
        if not proposed_lwd: return Response({"detail": "Valid proposed_last_working_date is required."}, status=400)
        resignation_date = parse_date(str(request.data.get("resignation_date", ""))) if request.data.get("resignation_date") else None
        if separation_type == "RESIGNATION" and not resignation_date: return Response({"detail": "Resignation date is required for resignation."}, status=400)
        try:
            notice_days = int(request.data.get("notice_days", 0)); waiver_days = int(request.data.get("notice_waiver_days", 0)); recovery = Decimal(str(request.data.get("notice_recovery_amount", 0)))
        except (TypeError, ValueError, InvalidOperation): return Response({"detail": "Invalid notice or recovery values."}, status=400)
        if min(notice_days, waiver_days) < 0 or waiver_days > notice_days or recovery < 0: return Response({"detail": "Invalid notice waiver/recovery values."}, status=400)
        case = ExitCase.objects.create(company=company, employee=employee, separation_type=separation_type, resignation_date=resignation_date, notice_days=notice_days, proposed_last_working_date=proposed_lwd, notice_waiver_days=waiver_days, notice_recovery_amount=recovery, reason=reason, created_by=request.user)
        ExitClearance.objects.bulk_create([ExitClearance(exit_case=case, clearance_type=t) for t, _ in ExitClearance.CLEARANCE_TYPES])
        _audit(case, request.user, "CREATE", "", "DRAFT", reason)
        case.refresh_from_db(); return Response(_payload(case), status=status.HTTP_201_CREATED)


class ExitCaseActionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, case_id):
        company = request_company(request)
        case = ExitCase.objects.select_for_update().select_related("employee", "employee__user").prefetch_related("clearances").filter(company=company, id=case_id).first()
        if not case: return Response({"detail": "Exit case not found."}, status=404)
        verb = str(request.data.get("action", "")).upper(); reason = str(request.data.get("reason", "")).strip(); old = case.status
        if verb == "START_NOTICE":
            if not has_feature_access(request, "hrms_exit_manage") or old != "DRAFT": return Response({"detail": "Invalid transition."}, status=400)
            lifecycle = EmployeeHrLifecycle.objects.select_for_update().get(employee=case.employee)
            lifecycle.employment_status = "NOTICE"; lifecycle.notice_start_date = case.resignation_date or timezone.localdate(); lifecycle.save()
            case.status = "NOTICE"
        elif verb == "START_CLEARANCE":
            if not has_feature_access(request, "hrms_exit_manage") or old not in {"DRAFT", "NOTICE"}: return Response({"detail": "Invalid transition."}, status=400)
            case.status = "CLEARANCE"
        elif verb == "SET_FINAL_SETTLEMENT_READY":
            if not has_feature_access(request, "hrms_exit_manage") or old not in {"CLEARANCE", "PENDING_APPROVAL"}: return Response({"detail": "Invalid transition."}, status=400)
            case.final_settlement_ready = bool(request.data.get("ready", True))
        elif verb == "SUBMIT_APPROVAL":
            if not has_feature_access(request, "hrms_exit_manage") or old != "CLEARANCE": return Response({"detail": "Exit case must be in clearance."}, status=400)
            blockers = list(case.clearances.exclude(status__in=["CLEARED", "WAIVED"]).values_list("clearance_type", flat=True))
            if blockers: return Response({"detail": "All exit clearances must be cleared or waived.", "blocking_clearances": blockers}, status=400)
            if not case.final_settlement_ready: return Response({"detail": "Final settlement must be ready before approval."}, status=400)
            approved_lwd = parse_date(str(request.data.get("approved_last_working_date", ""))) or case.proposed_last_working_date
            case.approved_last_working_date = approved_lwd; case.status = "PENDING_APPROVAL"
        elif verb == "APPROVE":
            if not has_feature_access(request, "hrms_exit_approve") or old != "PENDING_APPROVAL": return Response({"detail": "Exit approval not allowed."}, status=403)
            if request.user.id in {case.created_by_id, case.employee.user_id}: return Response({"detail": "Self-approval/creator approval is not allowed."}, status=403)
            case.approved_by = request.user; case.approved_at = timezone.now(); case.status = "APPROVED"
        elif verb == "SEPARATE":
            if old == "SEPARATED": return Response(_payload(case))
            if not has_feature_access(request, "hrms_exit_approve") or old != "APPROVED": return Response({"detail": "Only approved exit cases can be separated."}, status=403)
            if request.user.id in {case.created_by_id, case.employee.user_id}: return Response({"detail": "Creator/employee cannot execute final separation."}, status=403)
            blockers = list(case.clearances.exclude(status__in=["CLEARED", "WAIVED"]).values_list("clearance_type", flat=True))
            if blockers or not case.final_settlement_ready or not case.approved_last_working_date: return Response({"detail": "Separation gates are not complete."}, status=400)
            lifecycle = EmployeeHrLifecycle.objects.select_for_update().get(employee=case.employee); before = lifecycle.employment_status
            lifecycle.employment_status = "SEPARATED"; lifecycle.last_working_date = case.approved_last_working_date; lifecycle.separation_type = case.separation_type; lifecycle.exit_reason = case.reason; lifecycle.save()
            employee = EmployeeProfile.objects.select_for_update().get(id=case.employee_id); employee.is_active = False; employee.save(update_fields=["is_active"])
            if employee.user_id:
                user = employee.user; user.is_active = False; user.save(update_fields=["is_active"])
            event = EmployeeHrLifecycleEvent.objects.create(employee=employee, event_type="SEPARATION", effective_date=case.approved_last_working_date, from_status=before, to_status="SEPARATED", note=case.reason, metadata={"exit_case_id": case.id, "separation_type": case.separation_type}, created_by=request.user)
            _create_letter(case, "SEPARATION", event, request.user)
            case.status = "SEPARATED"; case.separated_at = timezone.now()
        elif verb == "CANCEL":
            if not has_feature_access(request, "hrms_exit_approve") or old in {"APPROVED", "SEPARATED"}: return Response({"detail": "This exit case cannot be cancelled."}, status=400)
            if not reason: return Response({"detail": "Cancellation reason is required."}, status=400)
            case.status = "CANCELLED"
        else: return Response({"detail": "Unsupported action."}, status=400)
        case.save(); _audit(case, request.user, verb, old, case.status, reason, {"final_settlement_ready": case.final_settlement_ready, "approved_last_working_date": case.approved_last_working_date.isoformat() if case.approved_last_working_date else None})
        case.refresh_from_db(); return Response(_payload(case))


class ExitClearanceActionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, case_id, clearance_id):
        if not has_feature_access(request, "hrms_exit_clearance"): return Response({"detail": "Exit clearance permission required."}, status=403)
        company = request_company(request)
        clearance = ExitClearance.objects.select_for_update().select_related("exit_case", "exit_case__employee").filter(exit_case__company=company, exit_case_id=case_id, id=clearance_id).first()
        if not clearance: return Response({"detail": "Clearance not found."}, status=404)
        case = clearance.exit_case
        if case.status not in {"NOTICE", "CLEARANCE"}: return Response({"detail": "Clearance can only be reviewed during notice/clearance."}, status=400)
        new_status = str(request.data.get("status", "")).upper()
        if new_status not in dict(ExitClearance.STATUS_CHOICES): return Response({"detail": "Invalid clearance status."}, status=400)
        waiver_reason = str(request.data.get("waiver_reason", "")).strip()
        if new_status == "WAIVED" and not waiver_reason: return Response({"detail": "Waiver reason is mandatory."}, status=400)
        old = clearance.status; clearance.status = new_status; clearance.note = str(request.data.get("note", "")); clearance.evidence = request.data.get("evidence") or {}; clearance.waiver_reason = waiver_reason if new_status == "WAIVED" else ""; clearance.reviewed_by = request.user; clearance.reviewed_at = timezone.now(); clearance.save()
        _audit(case, request.user, "CLEARANCE_" + new_status, old, new_status, waiver_reason or clearance.note, {"clearance_id": clearance.id, "clearance_type": clearance.clearance_type})
        return Response(_clearance_payload(clearance))


class ExitPostSeparationLetterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, case_id):
        if not has_feature_access(request, "hrms_letters_manage"): return Response({"detail": "HR letter manage permission required."}, status=403)
        company = request_company(request)
        case = ExitCase.objects.select_for_update().select_related("employee").filter(company=company, id=case_id).first()
        if not case: return Response({"detail": "Exit case not found."}, status=404)
        if case.status != "SEPARATED": return Response({"detail": "Experience/relieving letters require completed separation."}, status=400)
        letter_type = str(request.data.get("letter_type", "")).upper()
        if letter_type not in {"EXPERIENCE", "RELIEVING"}: return Response({"detail": "letter_type must be EXPERIENCE or RELIEVING."}, status=400)
        existing = HrLetterWorkflow.objects.filter(company=company, employee=case.employee, letter_type=letter_type, context__exit_case_id=case.id).order_by("-id").first()
        if existing: return Response({"id": existing.id, "letter_type": existing.letter_type, "status": existing.status})
        event = case.employee.hr_lifecycle_events.filter(event_type="SEPARATION", metadata__exit_case_id=case.id).first()
        flow = _create_letter(case, letter_type, event, request.user)
        if not flow: return Response({"detail": "No active approved-compatible template is configured for this letter type."}, status=400)
        _audit(case, request.user, "CREATE_" + letter_type + "_LETTER", "SEPARATED", "SEPARATED", metadata={"letter_workflow_id": flow.id})
        return Response({"id": flow.id, "letter_type": flow.letter_type, "status": flow.status}, status=status.HTTP_201_CREATED)
