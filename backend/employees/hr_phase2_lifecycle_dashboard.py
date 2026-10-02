from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.access import HasRequiredFeature, request_company
from .models import EmployeeProfile, EmployeeCareerMovement
from .hr_lifecycle_models import EmployeeHrLifecycle, EmployeeHrLifecycleEvent
from .hr_phase2_lifecycle_models import EmployeeLifecycleAction, EmployeeLifecycleAudit, ExitCase
from .hr_phase2_letters_bgv_models import BackgroundVerificationCase, HrLetterWorkflow
from .hr_phase2_ats_models import HrLetter


def _iso(value):
    return value.isoformat() if value else None


def _timeline(employee, company):
    items = []
    if employee.joining_date:
        items.append({"kind": "JOINING", "date": _iso(employee.joining_date), "title": "Employee joined", "status": "COMPLETED", "ref_id": employee.id})
    bgv = BackgroundVerificationCase.objects.filter(company=company, employee=employee).first()
    if bgv:
        items.append({"kind": "BGV", "date": _iso(bgv.decided_at or bgv.created_at), "title": "Background verification", "status": bgv.overall_status, "ref_id": bgv.id})
    for event in EmployeeHrLifecycleEvent.objects.filter(employee=employee):
        items.append({"kind": "LIFECYCLE", "date": _iso(event.effective_date), "title": event.event_type.replace("_", " ").title(), "status": event.to_status, "note": event.note, "ref_id": event.id})
    for action in EmployeeLifecycleAction.objects.filter(company=company, employee=employee):
        items.append({"kind": "ACTION", "date": _iso(action.effective_date), "title": action.action_type.replace("_", " ").title(), "status": action.status, "note": action.reason, "ref_id": action.id})
    for movement in EmployeeCareerMovement.objects.filter(employee=employee):
        items.append({"kind": "CAREER", "date": _iso(movement.effective_date), "title": movement.get_movement_type_display(), "status": movement.status, "note": movement.reason, "ref_id": movement.id})
    exit_case = ExitCase.objects.filter(company=company, employee=employee).prefetch_related("clearances").first()
    if exit_case:
        items.append({"kind": "EXIT", "date": _iso(exit_case.approved_last_working_date or exit_case.proposed_last_working_date), "title": exit_case.get_separation_type_display(), "status": exit_case.status, "note": exit_case.reason, "ref_id": exit_case.id, "clearances": [{"type": x.clearance_type, "status": x.status} for x in exit_case.clearances.all()]})
    for workflow in HrLetterWorkflow.objects.filter(company=company, employee=employee):
        items.append({"kind": "LETTER_WORKFLOW", "date": _iso(workflow.effective_date), "title": workflow.get_letter_type_display(), "status": workflow.status, "ref_id": workflow.id})
    for letter in HrLetter.objects.filter(company=company, employee=employee):
        items.append({"kind": "ISSUED_LETTER", "date": _iso(letter.issued_at), "title": letter.get_letter_type_display(), "status": letter.acknowledgement_status, "ref_id": letter.id, "content_hash": letter.content_hash})
    items.sort(key=lambda x: x.get("date") or "", reverse=True)
    return items


class EmployeeLifecycleTimelineAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_lifecycle_view"

    def get(self, request, employee_id):
        company = request_company(request)
        employee = EmployeeProfile.objects.filter(company=company, id=employee_id).first()
        if not employee:
            return Response({"detail": "Employee not found in active company."}, status=404)
        lifecycle = EmployeeHrLifecycle.objects.filter(employee=employee).first()
        return Response({
            "employee_id": employee.id, "employee_code": employee.employee_id,
            "employment_status": lifecycle.employment_status if lifecycle else None,
            "hr_stage": lifecycle.hr_stage if lifecycle else None,
            "timeline": _timeline(employee, company),
        })


class EmployeeLifecycleCommandCenterAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_lifecycle_view"

    def get(self, request):
        company = request_company(request); today = timezone.localdate()
        month_start = today.replace(day=1)
        probation = EmployeeHrLifecycle.objects.filter(employee__company=company, employment_type="PROBATION")
        actions = EmployeeLifecycleAction.objects.filter(company=company)
        exits = ExitCase.objects.filter(company=company)
        pending_statuses = ["DRAFT", "MANAGER_REVIEW", "HR_REVIEW", "PENDING_APPROVAL", "APPROVED"]
        pending_changes = actions.filter(action_type__in=["PROMOTION", "INCREMENT", "TRANSFER"], status__in=pending_statuses)
        confirmation_pending = actions.filter(action_type="CONFIRMATION", status__in=pending_statuses)
        on_notice = EmployeeHrLifecycle.objects.filter(employee__company=company, employment_status="NOTICE")
        clearance_pending = exits.filter(status__in=["NOTICE", "CLEARANCE"]).filter(Q(clearances__status__in=["PENDING", "BLOCKED"])).distinct()
        settlement_pending = exits.filter(status="CLEARANCE", final_settlement_ready=False)
        approval_pending = exits.filter(status="PENDING_APPROVAL")
        separated_month = exits.filter(status="SEPARATED", approved_last_working_date__gte=month_start, approved_last_working_date__lte=today)
        return Response({
            "as_of": today,
            "probation_due": probation.filter(confirmation_due_date__gte=today).count(),
            "probation_overdue": probation.filter(confirmation_due_date__lt=today).count(),
            "confirmation_pending": confirmation_pending.count(),
            "career_change_pending": pending_changes.count(),
            "promotion_pending": pending_changes.filter(action_type="PROMOTION").count(),
            "increment_pending": pending_changes.filter(action_type="INCREMENT").count(),
            "transfer_pending": pending_changes.filter(action_type="TRANSFER").count(),
            "employees_on_notice": on_notice.count(),
            "exit_clearance_pending": clearance_pending.count(),
            "final_settlement_pending": settlement_pending.count(),
            "separation_approval_pending": approval_pending.count(),
            "separations_this_month": separated_month.count(),
            "queues": {
                "probation_overdue_employee_ids": list(probation.filter(confirmation_due_date__lt=today).values_list("employee_id", flat=True)[:200]),
                "pending_lifecycle_action_ids": list(actions.filter(status__in=pending_statuses).values_list("id", flat=True)[:200]),
                "pending_exit_case_ids": list(exits.filter(status__in=["NOTICE", "CLEARANCE", "PENDING_APPROVAL", "APPROVED"]).values_list("id", flat=True)[:200]),
            },
        })
