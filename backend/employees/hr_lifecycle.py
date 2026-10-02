from calendar import monthrange
from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from attendance.models import Attendance
from tenancy.access import HasRequiredFeature, request_company

from .hr_lifecycle_models import EmployeeHrLifecycle, EmployeeHrLifecycleEvent, _add_months
from .models import (
    EmployeeDocument,
    EmployeePenalty,
    EmployeeProfile,
    EmployeeTrainingAssignment,
    LeaveRequest,
    PayrollRecord,
    PerformanceReview,
)

REQUIRED_DOCUMENT_TYPES = ("AADHAAR", "PAN", "ADDRESS_PROOF", "BANK_PROOF", "PHOTO")


def _role(request):
    return str(getattr(request.user, "role", "") or "").upper()


def _company_employee(request, employee_id):
    company = request_company(request)
    if company is None:
        return None
    return EmployeeProfile.objects.filter(pk=employee_id, company=company).select_related(
        "user", "reporting_manager__user", "company"
    ).first()


def _lifecycle(employee):
    start = employee.joining_date or timezone.localdate()
    row, _ = EmployeeHrLifecycle.objects.get_or_create(
        employee=employee,
        defaults={
            "probation_start_date": start,
            "confirmation_due_date": _add_months(start, 3),
        },
    )
    return row


def _document_compliance(employee):
    docs = list(employee.hr_documents.all())
    present = {str(row.document_type or "").upper() for row in docs}
    missing = [kind for kind in REQUIRED_DOCUMENT_TYPES if kind not in present]
    unverified = [row for row in docs if not row.verified]
    expired = [
        row for row in docs
        if row.expiry_date is not None and row.expiry_date < timezone.localdate()
    ]
    return {
        "missing": missing,
        "missing_count": len(missing),
        "unverified_count": len(unverified),
        "expired_count": len(expired),
        "complete": not missing and not unverified and not expired,
    }


def _training_compliance(employee):
    rows = employee.training_assignments.filter(course__is_active=True, course__is_mandatory=True)
    pending = rows.exclude(status="COMPLETED").count()
    return {
        "mandatory": rows.count(),
        "completed": rows.filter(status="COMPLETED").count(),
        "pending": pending,
        "complete": pending == 0,
    }


def _readiness(employee, lifecycle):
    documents = _document_compliance(employee)
    training = _training_compliance(employee)
    profile_complete = bool(
        employee.user.first_name
        and employee.joining_date
        and employee.designation
        and employee.department
        and employee.job_title
        and employee.emergency_contact
    )
    security_complete = bool(
        employee.photo
        and employee.face_enrollment_verified
        and employee.attendance_device_id
    )
    acknowledgements_complete = bool(
        lifecycle.policy_acknowledged
        and lifecycle.sop_acknowledged
        and lifecycle.safety_training_acknowledged
    )
    hr_review_complete = lifecycle.hr_review_status == "APPROVED"
    checks = {
        "profile": profile_complete,
        "documents": documents["complete"],
        "security": security_complete,
        "training": training["complete"],
        "acknowledgements": acknowledgements_complete,
        "payroll": lifecycle.payroll_details_complete,
        "role_access": lifecycle.role_access_assigned,
        "hr_review": hr_review_complete,
    }
    ready = all(checks.values()) or lifecycle.hr_override_ready
    if not profile_complete:
        stage = "PROFILE_PENDING"
    elif not documents["complete"]:
        stage = "DOCUMENT_PENDING"
    elif not security_complete:
        stage = "SECURITY_PENDING"
    elif not training["complete"] or not acknowledgements_complete:
        stage = "TRAINING_PENDING"
    elif not lifecycle.payroll_details_complete or not lifecycle.role_access_assigned or not hr_review_complete:
        stage = "HR_REVIEW"
    else:
        stage = "READY"
    if lifecycle.hr_override_ready:
        stage = "READY"
    if lifecycle.hr_stage != stage:
        lifecycle.hr_stage = stage
        lifecycle.save(update_fields=["hr_stage", "updated_at"])
    return {
        "ready": ready,
        "stage": stage,
        "checks": checks,
        "documents": documents,
        "training": training,
        "override": lifecycle.hr_override_ready,
    }


def _lifecycle_payload(employee, lifecycle=None):
    lifecycle = lifecycle or _lifecycle(employee)
    readiness = _readiness(employee, lifecycle)
    return {
        "employment_type": lifecycle.employment_type,
        "employment_status": lifecycle.employment_status,
        "hr_stage": lifecycle.hr_stage,
        "work_location": lifecycle.work_location,
        "probation_months": lifecycle.probation_months,
        "probation_start_date": lifecycle.probation_start_date,
        "confirmation_due_date": lifecycle.confirmation_due_date,
        "confirmed_at": lifecycle.confirmed_at,
        "manager_review_status": lifecycle.manager_review_status,
        "manager_review_note": lifecycle.manager_review_note,
        "hr_review_status": lifecycle.hr_review_status,
        "hr_review_note": lifecycle.hr_review_note,
        "policy_acknowledged": lifecycle.policy_acknowledged,
        "sop_acknowledged": lifecycle.sop_acknowledged,
        "safety_training_acknowledged": lifecycle.safety_training_acknowledged,
        "payroll_details_complete": lifecycle.payroll_details_complete,
        "role_access_assigned": lifecycle.role_access_assigned,
        "joining_checklist": lifecycle.joining_checklist,
        "compensation_profile": lifecycle.compensation_profile,
        "notice_start_date": lifecycle.notice_start_date,
        "last_working_date": lifecycle.last_working_date,
        "separation_type": lifecycle.separation_type,
        "exit_reason": lifecycle.exit_reason,
        "readiness": readiness,
    }


class CorporateHrDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    def get(self, request):
        company = request_company(request)
        if company is None:
            return Response({"detail": "Active company workspace not found."}, status=403)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        month_end = today.replace(day=monthrange(today.year, today.month)[1])
        employees = EmployeeProfile.objects.filter(company=company, is_active=True).select_related("user")
        employee_ids = list(employees.values_list("id", flat=True))
        lifecycle_rows = EmployeeHrLifecycle.objects.filter(employee_id__in=employee_ids)
        present_today = Attendance.objects.filter(employee_id__in=employee_ids, date=today).exclude(status="ABSENT").values("employee_id").distinct().count()
        new_joiners = employees.filter(joining_date__gte=today - timedelta(days=30), joining_date__lte=today).count()
        probation = lifecycle_rows.filter(employment_status="PROBATION").count()
        confirmation_due = lifecycle_rows.filter(
            employment_status="PROBATION",
            confirmation_due_date__lte=today + timedelta(days=30),
        ).count()
        onboarding_pending = lifecycle_rows.exclude(hr_stage="READY").count() + max(0, len(employee_ids) - lifecycle_rows.count())
        leave_pending = LeaveRequest.objects.filter(employee_id__in=employee_ids, status="PENDING").count()
        payroll = PayrollRecord.objects.filter(employee_id__in=employee_ids, payroll_month=month_start)
        penalties = EmployeePenalty.objects.filter(employee_id__in=employee_ids)
        performance = PerformanceReview.objects.filter(employee_id__in=employee_ids, period_end__gte=month_start)
        training = EmployeeTrainingAssignment.objects.filter(employee_id__in=employee_ids, course__is_mandatory=True, course__is_active=True)
        docs = EmployeeDocument.objects.filter(employee_id__in=employee_ids)
        missing_required = 0
        for employee in employees.prefetch_related("hr_documents"):
            missing_required += _document_compliance(employee)["missing_count"]
        designation_mix = {}
        department_mix = {}
        for employee in employees:
            designation = employee.get_designation_display()
            department = employee.department or "Unassigned"
            designation_mix[designation] = designation_mix.get(designation, 0) + 1
            department_mix[department] = department_mix.get(department, 0) + 1
        return Response({
            "scope": "CORPORATE_HR",
            "as_of": today,
            "workforce": {
                "active": len(employee_ids),
                "present_today": present_today,
                "absent_or_not_checked_in": max(0, len(employee_ids) - present_today),
                "new_joiners_30d": new_joiners,
                "probation": probation,
                "confirmation_due_30d": confirmation_due,
                "pending_onboarding": onboarding_pending,
                "notice_period": lifecycle_rows.filter(employment_status="NOTICE").count(),
                "designation_mix": designation_mix,
                "department_mix": department_mix,
            },
            "approvals": {
                "leave": leave_pending,
                "payroll": payroll.filter(status="DRAFT").count(),
                "penalty": penalties.filter(status="DRAFT").count(),
                "performance": performance.exclude(status__in=["FINAL", "ACKNOWLEDGED"]).count(),
            },
            "compliance": {
                "missing_required_documents": missing_required,
                "unverified_documents": docs.filter(verified=False).count(),
                "expired_documents": docs.filter(expiry_date__lt=today).count(),
                "training_overdue": training.filter(status="OVERDUE").count(),
                "training_pending": training.exclude(status="COMPLETED").count(),
            },
            "payroll": {
                "month": month_start.strftime("%Y-%m"),
                "draft": payroll.filter(status="DRAFT").count(),
                "approved": payroll.filter(status="APPROVED").count(),
                "paid": payroll.filter(status="PAID").count(),
                "net_salary": str(payroll.aggregate(total=Sum("net_salary"))["total"] or 0),
            },
        })


class EmployeeHrDirectoryAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    def get(self, request):
        company = request_company(request)
        if company is None:
            return Response({"detail": "Active company workspace not found."}, status=403)
        employees = EmployeeProfile.objects.filter(company=company).select_related(
            "user", "reporting_manager__user"
        ).prefetch_related("hr_documents", "training_assignments__course")
        rows = []
        for employee in employees:
            lifecycle = _lifecycle(employee)
            rows.append({
                "id": employee.id,
                "employee_id": employee.employee_id,
                "name": employee.user.get_full_name() or employee.user.phone,
                "phone": employee.user.phone,
                "email": employee.user.email,
                "designation": employee.designation,
                "job_title": employee.job_title,
                "department": employee.department,
                "grade": employee.grade,
                "joining_date": employee.joining_date,
                "is_active": bool(employee.is_active and employee.user.is_active),
                "reporting_manager": None if employee.reporting_manager is None else (
                    employee.reporting_manager.user.get_full_name() or employee.reporting_manager.user.phone
                ),
                "lifecycle": _lifecycle_payload(employee, lifecycle),
            })
        return Response({"employees": rows})


class EmployeeDigitalHrFileAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    def get(self, request, employee_id):
        employee = _company_employee(request, employee_id)
        if employee is None:
            return Response({"detail": "Employee not found."}, status=404)
        lifecycle = _lifecycle(employee)
        documents = employee.hr_documents.all().order_by("document_type")
        attendance = Attendance.objects.filter(employee=employee).order_by("-date")[:31]
        leaves = employee.leave_requests.all()[:25]
        payroll = employee.payroll_records.all()[:12]
        penalties = employee.penalties.all()[:25]
        training = employee.training_assignments.select_related("course").all()[:50]
        performance = employee.performance_reviews.all()[:20]
        career = employee.career_movements.select_related("created_by", "approved_by").all()[:30]
        events = employee.hr_lifecycle_events.select_related("created_by").all()[:100]
        return Response({
            "employee": {
                "id": employee.id,
                "employee_id": employee.employee_id,
                "name": employee.user.get_full_name() or employee.user.phone,
                "phone": employee.user.phone,
                "email": employee.user.email,
                "date_of_birth": employee.date_of_birth,
                "gender": employee.gender,
                "address": employee.address,
                "city": employee.city,
                "state": employee.state,
                "pincode": employee.pincode,
                "emergency_name": employee.emergency_name,
                "emergency_contact": employee.emergency_contact,
                "joining_date": employee.joining_date,
                "designation": employee.designation,
                "job_title": employee.job_title,
                "department": employee.department,
                "grade": employee.grade,
                "salary": employee.salary if _role(request) in {"ADMIN", "MANAGER"} else None,
                "reporting_manager": None if employee.reporting_manager is None else (
                    employee.reporting_manager.user.get_full_name() or employee.reporting_manager.user.phone
                ),
                "face_verified": employee.face_enrollment_verified,
                "attendance_device_bound": bool(employee.attendance_device_id),
                "id_card_issued_at": employee.id_card_issued_at,
                "id_card_valid_until": employee.id_card_valid_until,
                "active": bool(employee.is_active and employee.user.is_active),
            },
            "lifecycle": _lifecycle_payload(employee, lifecycle),
            "documents": [{
                "id": row.id,
                "type": row.document_type,
                "number": row.document_number,
                "verified": row.verified,
                "expiry_date": row.expiry_date,
                "uploaded_at": row.uploaded_at,
            } for row in documents],
            "attendance": [{
                "date": row.date,
                "status": row.status,
                "working_hours": row.working_hours,
                "check_in": row.check_in,
                "check_out": row.check_out,
            } for row in attendance],
            "leave": [{
                "id": row.id,
                "type": row.leave_type,
                "start": row.start_date,
                "end": row.end_date,
                "status": row.status,
                "reason": row.reason,
            } for row in leaves],
            "payroll": [{
                "id": row.id,
                "month": row.payroll_month,
                "net_salary": row.net_salary,
                "status": row.status,
                "overtime_amount": row.overtime_amount,
                "other_deductions": row.other_deductions,
            } for row in payroll],
            "penalties": [{
                "id": row.id,
                "date": row.penalty_date,
                "amount": row.amount,
                "reason": row.reason,
                "status": row.status,
            } for row in penalties],
            "training": [{
                "id": row.id,
                "course": row.course.title,
                "status": row.status,
                "due_date": row.due_date,
            } for row in training],
            "performance": [{
                "id": row.id,
                "period_start": row.period_start,
                "period_end": row.period_end,
                "overall_score": row.overall_score,
                "status": row.status,
            } for row in performance],
            "career": [{
                "id": row.id,
                "type": row.movement_type,
                "effective_date": row.effective_date,
                "status": row.status,
                "old_job_title": row.old_job_title,
                "new_job_title": row.new_job_title,
                "old_department": row.old_department,
                "new_department": row.new_department,
                "reason": row.reason,
            } for row in career],
            "audit": [{
                "id": row.id,
                "type": row.event_type,
                "effective_date": row.effective_date,
                "from": row.from_status,
                "to": row.to_status,
                "note": row.note,
                "by": row.created_by.get_full_name() or row.created_by.phone,
                "created_at": row.created_at,
            } for row in events],
        })

    @transaction.atomic
    def patch(self, request, employee_id):
        employee = _company_employee(request, employee_id)
        if employee is None:
            return Response({"detail": "Employee not found."}, status=404)
        if _role(request) not in {"ADMIN", "MANAGER", "OFFICE"}:
            return Response({"detail": "HR lifecycle permission required."}, status=403)
        lifecycle = _lifecycle(employee)
        before = lifecycle.hr_stage
        allowed_fields = {
            "employment_type", "work_location", "probation_months",
            "policy_acknowledged", "sop_acknowledged", "safety_training_acknowledged",
            "payroll_details_complete", "role_access_assigned", "joining_checklist",
            "compensation_profile", "manager_review_note", "hr_review_note",
        }
        for field in allowed_fields:
            if field in request.data:
                setattr(lifecycle, field, request.data[field])
        if "probation_months" in request.data:
            months = max(1, min(24, int(request.data.get("probation_months") or 3)))
            lifecycle.probation_months = months
            start = lifecycle.probation_start_date or employee.joining_date or timezone.localdate()
            lifecycle.probation_start_date = start
            lifecycle.confirmation_due_date = _add_months(start, months)
        lifecycle.save()
        payload = _lifecycle_payload(employee, lifecycle)
        EmployeeHrLifecycleEvent.objects.create(
            employee=employee,
            event_type="LIFECYCLE_UPDATED",
            from_status=before,
            to_status=lifecycle.hr_stage,
            note=str(request.data.get("note") or "HR lifecycle details updated."),
            created_by=request.user,
        )
        return Response(payload)


class EmployeeHrLifecycleActionAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    @transaction.atomic
    def post(self, request, employee_id):
        employee = _company_employee(request, employee_id)
        if employee is None:
            return Response({"detail": "Employee not found."}, status=404)
        if _role(request) not in {"ADMIN", "MANAGER", "OFFICE"}:
            return Response({"detail": "HR lifecycle permission required."}, status=403)
        lifecycle = _lifecycle(employee)
        action = str(request.data.get("action") or "").upper()
        note = str(request.data.get("note") or "").strip()
        before = lifecycle.employment_status
        today = timezone.localdate()
        event_type = action

        if action == "MANAGER_REVIEW":
            lifecycle.manager_review_status = str(request.data.get("status") or "APPROVED").upper()
            lifecycle.manager_review_note = note
        elif action == "HR_REVIEW":
            lifecycle.hr_review_status = str(request.data.get("status") or "APPROVED").upper()
            lifecycle.hr_review_note = note
        elif action == "EXTEND_PROBATION":
            months = max(1, min(12, int(request.data.get("months") or 1)))
            lifecycle.employment_status = "PROBATION"
            lifecycle.confirmation_due_date = _add_months(lifecycle.confirmation_due_date or today, months)
            lifecycle.probation_months += months
        elif action == "CONFIRM":
            if lifecycle.manager_review_status != "APPROVED" or lifecycle.hr_review_status != "APPROVED":
                return Response({"detail": "Manager and HR reviews must be approved before confirmation."}, status=409)
            lifecycle.employment_status = "CONFIRMED"
            lifecycle.employment_type = "PERMANENT"
            lifecycle.confirmed_at = today
        elif action == "START_NOTICE":
            lifecycle.employment_status = "NOTICE"
            lifecycle.notice_start_date = today
            lifecycle.last_working_date = request.data.get("last_working_date") or lifecycle.last_working_date
            lifecycle.separation_type = str(request.data.get("separation_type") or "RESIGNATION")[:40]
            lifecycle.exit_reason = note
        elif action == "SEPARATE":
            lifecycle.employment_status = "SEPARATED"
            lifecycle.last_working_date = request.data.get("last_working_date") or today
            lifecycle.exit_reason = note or lifecycle.exit_reason
            employee.is_active = False
            employee.is_online = False
            employee.save(update_fields=["is_active", "is_online"])
            employee.user.is_active = False
            employee.user.save(update_fields=["is_active"])
        elif action == "OVERRIDE_READY":
            if not note:
                return Response({"detail": "HR override reason is required."}, status=400)
            lifecycle.hr_override_ready = True
            lifecycle.hr_override_reason = note[:500]
        elif action == "REMOVE_READY_OVERRIDE":
            lifecycle.hr_override_ready = False
            lifecycle.hr_override_reason = ""
        else:
            return Response({"detail": "Unsupported HR lifecycle action."}, status=400)

        lifecycle.save()
        payload = _lifecycle_payload(employee, lifecycle)
        EmployeeHrLifecycleEvent.objects.create(
            employee=employee,
            event_type=event_type,
            from_status=before,
            to_status=lifecycle.employment_status,
            note=note,
            metadata={"hr_stage": lifecycle.hr_stage},
            created_by=request.user,
        )
        return Response({"success": True, "lifecycle": payload})
