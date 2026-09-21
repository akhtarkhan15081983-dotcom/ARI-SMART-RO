import calendar
from io import BytesIO
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from tenancy.access import HasRequiredFeature, has_feature_access

from attendance.models import Attendance
from attendance.work_hours import reconcile_open_attendance
from installation.models import Installation
from jobs.models import Job
from .models import EmployeeDocument, EmployeePenalty, EmployeeProfile, EmployeeTrainingAssignment, Holiday, HRPolicy, LeaveRequest, PayrollRecord, PerformanceReview


MONEY = Decimal("0.01")


def _money(value):
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def _role(user, *roles):
    return getattr(user, "role", "") in roles


def _month(value):
    parsed = datetime.strptime(value, "%Y-%m").date()
    return parsed.replace(day=1)


def calculate_payroll(employee, payroll_month):
    policy = HRPolicy.current()
    reconcile_open_attendance(employee=employee)
    days_in_month = calendar.monthrange(payroll_month.year, payroll_month.month)[1]
    month_end = payroll_month.replace(day=days_in_month)
    start = max(payroll_month, employee.joining_date)
    daily_rate = Decimal(employee.salary) / Decimal(days_in_month)
    eligible_days = Decimal((month_end - start).days + 1)
    payable_base = _money(daily_rate * eligible_days)
    hourly_rate = daily_rate / Decimal(policy.daily_work_hours)
    attendance = list(Attendance.objects.filter(employee=employee, date__range=(start, month_end)))
    attendance_by_date = {row.date: row for row in attendance}
    holiday_dates = set(Holiday.objects.filter(date__range=(start, month_end)).values_list("date", flat=True))
    leaves = list(LeaveRequest.objects.filter(employee=employee, status="APPROVED", start_date__lte=month_end, end_date__gte=start).order_by("created_at"))

    full_paid_remaining = policy.monthly_paid_leaves
    half_paid_remaining = policy.monthly_paid_half_days
    paid_leave_dates, unpaid_leave_units = set(), Decimal("0")
    for leave in leaves:
        current = max(start, leave.start_date)
        final = min(month_end, leave.end_date)
        while current <= final:
            if leave.leave_type == "HALF_DAY":
                if half_paid_remaining > 0:
                    paid_leave_dates.add((current, "HALF"))
                    half_paid_remaining -= 1
                else:
                    unpaid_leave_units += Decimal("0.5")
            elif full_paid_remaining > 0:
                paid_leave_dates.add((current, "FULL"))
                full_paid_remaining -= 1
            else:
                unpaid_leave_units += Decimal("1")
            current += timedelta(days=1)

    late_days = half_day_units = 0
    overtime_hours = Decimal("0")
    short_hours = Decimal("0")
    absent_days = 0
    current = start
    while current <= month_end:
        row = attendance_by_date.get(current)
        if current in holiday_dates and row is None:
            current += timedelta(days=1)
            continue
        full_leave = (current, "FULL") in paid_leave_dates
        half_leave = (current, "HALF") in paid_leave_dates
        if row is None:
            if not full_leave:
                absent_days += Decimal("0.5") if half_leave else Decimal("1")
        else:
            is_half_day = False
            if row.check_in:
                local_checkin = timezone.localtime(row.check_in).time().replace(tzinfo=None)
                if local_checkin >= policy.half_day_cutoff:
                    half_day_units += 1
                    is_half_day = True
                elif local_checkin > policy.office_start_time:
                    late_days += 1
            if row.status == "HALF_DAY" and not is_half_day:
                half_day_units += 1
                is_half_day = True

            regular_hours = Decimal(row.regular_working_hours or row.working_hours or 0)
            if not is_half_day:
                short_hours += max(
                    Decimal("0"),
                    Decimal(policy.daily_work_hours) - regular_hours,
                )
            overtime_hours += Decimal(row.overtime_working_hours or 0)
        current += timedelta(days=1)

    absence_deduction = _money((absent_days + unpaid_leave_units) * daily_rate)
    half_day_deduction = _money(Decimal(half_day_units) * daily_rate / Decimal("2"))
    late_penalty = _money(Decimal(late_days) * policy.late_penalty_amount)
    short_hours_deduction = _money(short_hours * hourly_rate)
    overtime_amount = _money(overtime_hours * hourly_rate)

    completed = Installation.objects.filter(engineer=employee, status="COMPLETED", completed_date__isnull=False)
    rent_count = sale_count = 0
    for installation in completed.only("business_type", "completed_date"):
        completed_local = timezone.localtime(installation.completed_date).date()
        distance = (payroll_month.year - completed_local.year) * 12 + payroll_month.month - completed_local.month
        if installation.business_type == "RENT" and 1 <= distance <= policy.rent_installation_incentive_months:
            rent_count += 1
        elif installation.business_type == "SALE" and distance == 1:
            sale_count += 1
    rent_incentive = _money(Decimal(rent_count) * policy.rent_installation_monthly_incentive)
    sale_incentive = _money(Decimal(sale_count) * policy.sale_installation_incentive)
    approved_penalties = EmployeePenalty.objects.filter(
        employee=employee,
        status="APPROVED",
        penalty_date__range=(start, month_end),
    )
    manual_penalty = _money(
        approved_penalties.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    )
    penalty_ids = list(approved_penalties.values_list("id", flat=True))
    work_penalty_days = 0
    work_penalty_jobs = []
    calculation_end = min(month_end, timezone.localdate())
    jobs = Job.objects.filter(
        engineer=employee,
        scheduled_date__date__lte=calculation_end,
    ).exclude(status="CANCELLED")
    for job in jobs.only("id", "job_id", "scheduled_date", "completed_at"):
        scheduled_day = timezone.localtime(job.scheduled_date).date()
        penalty_start = scheduled_day + timedelta(days=2)
        completed_day = (
            timezone.localtime(job.completed_at).date()
            if job.completed_at else calculation_end
        )
        penalty_end = min(completed_day, calculation_end)
        range_start = max(start, penalty_start)
        if penalty_end < range_start:
            continue
        days = (penalty_end - range_start).days + 1
        work_penalty_days += days
        work_penalty_jobs.append({
            "job_id": job.job_id,
            "penalty_days": days,
            "amount": str(_money(Decimal(days) * Decimal("10"))),
        })
    work_delay_penalty = _money(Decimal(work_penalty_days) * Decimal("10"))
    total_other_deductions = _money(manual_penalty + work_delay_penalty)
    net = _money(
        payable_base
        - late_penalty
        - half_day_deduction
        - absence_deduction
        - short_hours_deduction
        - total_other_deductions
        + overtime_amount
        + rent_incentive
        + sale_incentive
    )
    return {
        "base_salary": _money(employee.salary), "payable_base": payable_base,
        "late_days": late_days, "late_penalty": late_penalty,
        "half_day_deduction": half_day_deduction, "absence_deduction": absence_deduction,
        "short_hours": short_hours.quantize(MONEY), "short_hours_deduction": short_hours_deduction,
        "overtime_hours": overtime_hours.quantize(MONEY), "overtime_amount": overtime_amount,
        "rent_incentive": rent_incentive, "sale_incentive": sale_incentive,
        "other_deductions": total_other_deductions, "net_salary": max(Decimal("0"), net),
        "snapshot": {"calendar_days": days_in_month, "absent_days": str(absent_days), "unpaid_leave_units": str(unpaid_leave_units), "rent_installations": rent_count, "sale_installations": sale_count, "daily_rate": str(_money(daily_rate)), "hourly_rate": str(_money(hourly_rate)), "short_hours": str(short_hours.quantize(MONEY)), "short_hours_deduction": str(short_hours_deduction), "manual_penalty_ids": penalty_ids, "manual_penalty_count": len(penalty_ids), "manual_penalty_amount": str(manual_penalty), "work_delay_penalty_days": work_penalty_days, "work_delay_penalty_amount": str(work_delay_penalty), "work_delay_penalty_rate": "10.00", "work_delay_penalty_jobs": work_penalty_jobs},
    }


class EmployeeHrmsDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    def get(self, request):
        today = timezone.localdate()
        month_start = today.replace(day=1)
        policy = HRPolicy.current()

        if _role(request.user, "ADMIN", "MANAGER", "OFFICE"):
            month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
            employees = EmployeeProfile.objects.filter(is_active=True).select_related("user")
            attendance = Attendance.objects.filter(date__range=(month_start, today))
            leaves = LeaveRequest.objects.filter(
                start_date__lte=month_end,
                end_date__gte=month_start,
            )
            payroll = PayrollRecord.objects.filter(payroll_month=month_start)
            penalties = EmployeePenalty.objects.filter(
                penalty_date__range=(month_start, today)
            )
            present_today = Attendance.objects.filter(
                date=today,
            ).exclude(status="ABSENT").values("employee_id").distinct().count()
            active_count = employees.count()
            pending_leaves = leaves.filter(status="PENDING").count()
            approved_leaves = leaves.filter(status="APPROVED").count()
            draft_payroll = payroll.filter(status="DRAFT").count()
            approved_payroll = payroll.filter(status="APPROVED").count()
            paid_payroll = payroll.filter(status="PAID").count()
            payroll_net = payroll.aggregate(total=Sum("net_salary"))["total"] or Decimal("0")
            overtime_amount = payroll.aggregate(total=Sum("overtime_amount"))["total"] or Decimal("0")
            incentives = (
                (payroll.aggregate(total=Sum("rent_incentive"))["total"] or Decimal("0"))
                + (payroll.aggregate(total=Sum("sale_incentive"))["total"] or Decimal("0"))
            )
            approved_penalties = penalties.filter(status="APPROVED").aggregate(
                total=Sum("amount")
            )["total"] or Decimal("0")
            document_rows = EmployeeDocument.objects.filter(employee__in=employees)
            expiring_documents = document_rows.filter(
                expiry_date__isnull=False,
                expiry_date__gte=today,
                expiry_date__lte=today + timedelta(days=30),
            ).count()
            expired_documents = document_rows.filter(
                expiry_date__isnull=False,
                expiry_date__lt=today,
            ).count()
            unverified_documents = document_rows.filter(verified=False).count()
            performance_rows = PerformanceReview.objects.filter(
                employee__in=employees,
                period_end__gte=month_start,
            )
            pending_performance_reviews = performance_rows.exclude(
                status__in=["FINAL", "ACKNOWLEDGED"]
            ).count()
            training_rows = EmployeeTrainingAssignment.objects.filter(employee__in=employees)
            training_overdue = training_rows.filter(status="OVERDUE").count()
            training_completed = training_rows.filter(status="COMPLETED").count()
            training_pending = training_rows.exclude(status="COMPLETED").count()

            designation_counts = {}
            for row in employees:
                label = row.get_designation_display()
                designation_counts[label] = designation_counts.get(label, 0) + 1

            return Response({
                "scope": "CORPORATE",
                "month": month_start.strftime("%Y-%m"),
                "workforce": {
                    "active_employees": active_count,
                    "present_today": present_today,
                    "absent_or_not_checked_in": max(0, active_count - present_today),
                    "designation_mix": designation_counts,
                },
                "approvals": {
                    "pending_leaves": pending_leaves,
                    "approved_leaves": approved_leaves,
                    "draft_payroll": draft_payroll,
                    "approved_payroll": approved_payroll,
                    "paid_payroll": paid_payroll,
                    "draft_penalties": penalties.filter(status="DRAFT").count(),
                },
                "payroll": {
                    "net_salary": str(_money(payroll_net)),
                    "overtime_amount": str(_money(overtime_amount)),
                    "incentives": str(_money(incentives)),
                    "approved_penalties": str(_money(approved_penalties)),
                },
                "attendance": {
                    "records_this_month": attendance.count(),
                    "half_days": attendance.filter(status="HALF_DAY").count(),
                    "absences": attendance.filter(status="ABSENT").count(),
                    "pending_selfie_reviews": attendance.filter(
                        identity_review_status="PENDING"
                    ).count(),
                },
                "compliance": {
                    "documents_expiring_30_days": expiring_documents,
                    "documents_expired": expired_documents,
                    "documents_unverified": unverified_documents,
                    "training_overdue": training_overdue,
                    "training_pending": training_pending,
                    "training_completed": training_completed,
                },
                "performance": {
                    "pending_reviews": pending_performance_reviews,
                    "reviews_this_period": performance_rows.count(),
                },
                "policy": {
                    "office_start_time": policy.office_start_time.strftime("%I:%M %p"),
                    "daily_work_hours": str(policy.daily_work_hours),
                    "late_penalty": str(policy.late_penalty_amount),
                    "monthly_paid_leaves": policy.monthly_paid_leaves,
                    "monthly_paid_half_days": policy.monthly_paid_half_days,
                },
            })

        try:
            employee = request.user.employee_profile
        except (AttributeError, EmployeeProfile.DoesNotExist):
            return Response({"detail": "Employee profile not found."}, status=404)

        attendance = Attendance.objects.filter(
            employee=employee, date__range=(month_start, today)
        )
        rows = list(attendance)
        total_hours = sum((Decimal(row.working_hours) for row in rows), Decimal("0"))
        overtime_hours = sum(
            (max(Decimal("0"), Decimal(row.working_hours) - Decimal(policy.daily_work_hours)) for row in rows),
            Decimal("0"),
        )
        late_days = 0
        half_days = 0
        for row in rows:
            if row.status == "HALF_DAY":
                half_days += 1
            if row.check_in:
                check_in = timezone.localtime(row.check_in).time().replace(tzinfo=None)
                if check_in >= policy.half_day_cutoff:
                    if row.status != "HALF_DAY":
                        half_days += 1
                elif check_in > policy.office_start_time:
                    late_days += 1

        month_leaves = LeaveRequest.objects.filter(
            employee=employee, start_date__lte=today.replace(day=calendar.monthrange(today.year, today.month)[1]),
            end_date__gte=month_start,
        )
        approved = month_leaves.filter(status="APPROVED")
        full_used = sum(
            ((min(row.end_date, today) - max(row.start_date, month_start)).days + 1 for row in approved if row.leave_type == "FULL_DAY"),
            0,
        )
        half_used = sum(
            ((min(row.end_date, today) - max(row.start_date, month_start)).days + 1 for row in approved if row.leave_type == "HALF_DAY"),
            0,
        )
        current_installations = Installation.objects.filter(
            engineer=employee,
            status="COMPLETED",
            completed_date__date__range=(month_start, today),
        )
        new_rent = current_installations.filter(business_type="RENT").count()
        new_sales = current_installations.filter(business_type="SALE").count()
        latest_payroll = PayrollRecord.objects.filter(employee=employee).first()

        return Response({
            "employee": {
                "name": employee.user.get_full_name() or employee.user.phone,
                "employee_id": employee.employee_id,
                "designation": employee.get_designation_display(),
                "joining_date": employee.joining_date,
            },
            "month": month_start.strftime("%Y-%m"),
            "attendance": {
                "present_days": attendance.exclude(status="ABSENT").count(),
                "half_days": half_days,
                "late_days": late_days,
                "total_hours": str(total_hours.quantize(MONEY)),
                "overtime_hours": str(overtime_hours.quantize(MONEY)),
                "pending_selfie_reviews": attendance.filter(identity_review_status="PENDING").count(),
            },
            "leave_balance": {
                "paid_full_allowed": policy.monthly_paid_leaves,
                "paid_full_used": full_used,
                "paid_full_remaining": max(0, policy.monthly_paid_leaves - full_used),
                "paid_half_allowed": policy.monthly_paid_half_days,
                "paid_half_used": half_used,
                "paid_half_remaining": max(0, policy.monthly_paid_half_days - half_used),
                "pending_requests": month_leaves.filter(status="PENDING").count(),
            },
            "earnings": {
                "monthly_salary": str(_money(employee.salary)),
                "new_rent_installations": new_rent,
                "new_sales": new_sales,
                "future_rent_monthly_incentive": str(_money(Decimal(new_rent) * policy.rent_installation_monthly_incentive)),
                "next_salary_sale_incentive": str(_money(Decimal(new_sales) * policy.sale_installation_incentive)),
            },
            "policy": {
                "office_start_time": policy.office_start_time.strftime("%I:%M %p"),
                "daily_work_hours": str(policy.daily_work_hours),
                "late_penalty": str(policy.late_penalty_amount),
                "leave_notice_days": policy.leave_notice_days,
            },
            "latest_payroll": None if latest_payroll is None else {
                "month": latest_payroll.payroll_month,
                "net_salary": str(latest_payroll.net_salary),
                "status": latest_payroll.status,
                "paid_at": latest_payroll.paid_at,
            },
        })


class HolidayAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    def get(self, request):
        year = request.query_params.get("year")
        rows = Holiday.objects.select_related("declared_by")
        if year:
            try:
                rows = rows.filter(date__year=int(year))
            except ValueError:
                return Response({"detail": "Year must be numeric."}, status=400)
        return Response({"holidays": [{
            "id": row.id,
            "date": row.date,
            "name": row.name,
            "description": row.description,
            "is_paid": row.is_paid,
            "declared_by": row.declared_by.get_full_name() or row.declared_by.phone,
        } for row in rows[:500]]})

    def post(self, request):
        if not has_feature_access(request, "hrms_holiday_manage"):
            return Response({"detail": "Holiday management permission is required."}, status=403)
        try:
            holiday_date = date.fromisoformat(request.data.get("date", ""))
        except ValueError:
            return Response({"detail": "Valid holiday date is required."}, status=400)
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"detail": "Holiday name is required."}, status=400)
        row, created = Holiday.objects.update_or_create(
            date=holiday_date,
            defaults={
                "name": name[:120],
                "description": (request.data.get("description") or "").strip()[:300],
                "is_paid": bool(request.data.get("is_paid", True)),
                "declared_by": request.user,
            },
        )
        return Response({"id": row.id, "detail": "Holiday declared successfully."}, status=201 if created else 200)


class HolidayDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    def delete(self, request, holiday_id):
        if not has_feature_access(request, "hrms_holiday_manage"):
            return Response({"detail": "Holiday management permission is required."}, status=403)
        deleted, _ = Holiday.objects.filter(pk=holiday_id).delete()
        if not deleted:
            return Response({"detail": "Holiday not found."}, status=404)
        return Response(status=204)


class LeaveRequestAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    def get(self, request):
        rows = LeaveRequest.objects.select_related("employee__user")
        if not _role(request.user, "ADMIN", "MANAGER", "OFFICE"):
            rows = rows.filter(employee__user=request.user)
        return Response({"leaves": [{"id": r.id, "employee": r.employee.employee_id, "employee_name": r.employee.user.get_full_name(), "type": r.leave_type, "start_date": r.start_date, "end_date": r.end_date, "reason": r.reason, "status": r.status, "is_paid": r.is_paid, "review_note": r.review_note} for r in rows[:500]]})

    def post(self, request):
        try:
            employee = request.user.employee_profile
            start = date.fromisoformat(request.data.get("start_date", ""))
            end = date.fromisoformat(request.data.get("end_date", ""))
        except (AttributeError, ValueError):
            return Response({"detail": "Valid employee and leave dates are required."}, status=400)

        leave_type = request.data.get("leave_type", "FULL_DAY")
        if leave_type not in {"FULL_DAY", "HALF_DAY"}:
            return Response({"detail": "Leave type must be FULL_DAY or HALF_DAY."}, status=400)

        policy = HRPolicy.current()
        if start < timezone.localdate() + timedelta(days=policy.leave_notice_days):
            return Response({"detail": "Leave must be requested at least 1 day in advance."}, status=400)
        if end < start:
            return Response({"detail": "End date cannot be before start date."}, status=400)

        active_requests = LeaveRequest.objects.filter(
            employee=employee,
            status__in=["PENDING", "APPROVED"],
        )
        if active_requests.filter(start_date__lte=end, end_date__gte=start).exists():
            return Response({"detail": "A leave request already exists for these dates."}, status=400)

        # Monthly policy: up to 2 full-day dates and 2 half-day dates
        # (or the values configured in HRPolicy). Pending requests reserve
        # their dates as well, so an employee cannot submit above the limit
        # while earlier requests are awaiting approval.
        month_cursor = start.replace(day=1)
        final_month = end.replace(day=1)
        monthly_limit = (
            policy.monthly_paid_half_days
            if leave_type == "HALF_DAY"
            else policy.monthly_paid_leaves
        )

        while month_cursor <= final_month:
            month_end = month_cursor.replace(
                day=calendar.monthrange(month_cursor.year, month_cursor.month)[1]
            )
            requested_start = max(start, month_cursor)
            requested_end = min(end, month_end)
            requested_dates = (requested_end - requested_start).days + 1

            existing_same_type = active_requests.filter(
                leave_type=leave_type,
                start_date__lte=month_end,
                end_date__gte=month_cursor,
            )
            used_dates = 0
            for existing in existing_same_type:
                overlap_start = max(existing.start_date, month_cursor)
                overlap_end = min(existing.end_date, month_end)
                used_dates += (overlap_end - overlap_start).days + 1

            if used_dates + requested_dates > monthly_limit:
                label = "half-day" if leave_type == "HALF_DAY" else "full-day"
                return Response(
                    {
                        "detail": (
                            f"Only {monthly_limit} {label} leave date(s) are "
                            "allowed per month. "
                            f"{used_dates} already requested/approved."
                        )
                    },
                    status=400,
                )

            if month_cursor.month == 12:
                month_cursor = date(month_cursor.year + 1, 1, 1)
            else:
                month_cursor = date(month_cursor.year, month_cursor.month + 1, 1)

        row = LeaveRequest.objects.create(
            employee=employee,
            leave_type=leave_type,
            start_date=start,
            end_date=end,
            reason=(request.data.get("reason") or "").strip(),
        )
        return Response(
            {"id": row.id, "status": row.status, "detail": "Leave request submitted for approval."},
            status=201,
        )


class LeaveReviewAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    def post(self, request, leave_id):
        if not has_feature_access(request, "hrms_leave_approve"):
            return Response({"detail": "Leave approval permission is required."}, status=403)
        row = LeaveRequest.objects.filter(pk=leave_id, status="PENDING").first()
        if row is None:
            return Response({"detail": "Pending leave not found."}, status=404)
        decision = request.data.get("status")
        if decision not in ("APPROVED", "REJECTED"):
            return Response({"detail": "Status must be APPROVED or REJECTED."}, status=400)
        row.status, row.reviewed_by, row.reviewed_at = decision, request.user, timezone.now()
        row.review_note = (request.data.get("review_note") or "").strip()
        row.is_paid = decision == "APPROVED"
        row.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note", "is_paid"])
        return Response({"detail": f"Leave {decision.lower()}."})


class PayrollAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    def get(self, request):
        rows = PayrollRecord.objects.select_related("employee__user")
        if has_feature_access(request, "hrms_payroll_manage"):
            if request.query_params.get("month"):
                rows = rows.filter(payroll_month=_month(request.query_params["month"]))
        else:
            rows = rows.filter(employee__user=request.user)
        return Response({"payroll": [{"id": r.id, "employee": r.employee.employee_id, "employee_name": r.employee.user.get_full_name(), "month": r.payroll_month, "base_salary": r.base_salary, "late_penalty": r.late_penalty, "half_day_deduction": r.half_day_deduction, "absence_deduction": r.absence_deduction, "overtime_hours": r.overtime_hours, "overtime_amount": r.overtime_amount, "rent_incentive": r.rent_incentive, "sale_incentive": r.sale_incentive, "other_earnings": r.other_earnings, "other_deductions": r.other_deductions, "net_salary": r.net_salary, "status": r.status, "snapshot": r.calculation_snapshot} for r in rows[:1000]]})

    @transaction.atomic
    def post(self, request):
        if not has_feature_access(request, "hrms_payroll_manage"):
            return Response({"detail": "Payroll management permission is required."}, status=403)
        try:
            month = _month(request.data.get("month", ""))
        except ValueError:
            return Response({"detail": "Month must be YYYY-MM."}, status=400)
        month_end = month.replace(day=calendar.monthrange(month.year, month.month)[1])
        if month_end >= timezone.localdate():
            return Response({"detail": "Payroll can be generated only after the month is complete."}, status=400)
        generated = 0
        for employee in EmployeeProfile.objects.filter(is_active=True, joining_date__lte=month_end):
            existing = PayrollRecord.objects.filter(employee=employee, payroll_month=month).first()
            if existing and existing.status != "DRAFT":
                continue
            result = calculate_payroll(employee, month)
            PayrollRecord.objects.update_or_create(employee=employee, payroll_month=month, defaults={
                "base_salary": result["base_salary"], "payable_base": result["payable_base"], "late_days": result["late_days"], "late_penalty": result["late_penalty"],
                "half_day_deduction": result["half_day_deduction"], "absence_deduction": result["absence_deduction"], "short_hours": result["short_hours"], "short_hours_deduction": result["short_hours_deduction"], "overtime_hours": result["overtime_hours"], "overtime_amount": result["overtime_amount"],
                "rent_incentive": result["rent_incentive"], "sale_incentive": result["sale_incentive"], "other_deductions": result["other_deductions"], "net_salary": result["net_salary"], "calculation_snapshot": result["snapshot"],
            })
            generated += 1
        return Response({"detail": "Payroll draft generated.", "records": generated})


class PayrollActionAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    def post(self, request, payroll_id):
        if not has_feature_access(request, "hrms_payroll_manage"):
            return Response({"detail": "Payroll management permission is required."}, status=403)
        row = PayrollRecord.objects.filter(pk=payroll_id).first()
        if row is None:
            return Response({"detail": "Payroll record not found."}, status=404)
        action = request.data.get("action")
        if action == "APPROVE" and row.status == "DRAFT":
            row.status, row.approved_by, row.approved_at = "APPROVED", request.user, timezone.now()
            row.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        elif action == "MARK_PAID" and row.status == "APPROVED":
            row.status, row.paid_at = "PAID", timezone.now()
            row.save(update_fields=["status", "paid_at", "updated_at"])
        else:
            return Response({"detail": "Invalid action for current payroll status."}, status=400)
        return Response({"detail": f"Payroll marked {row.status.lower()}."})


class EmployeePenaltyAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    def get(self, request):
        rows = EmployeePenalty.objects.select_related("employee__user", "created_by", "approved_by")
        if not _role(request.user, "ADMIN", "MANAGER", "OFFICE"):
            rows = rows.filter(employee__user=request.user)
        data = [{
            "id": row.id,
            "employee_id": row.employee_id,
            "employee": row.employee.employee_id,
            "employee_name": row.employee.user.get_full_name() or row.employee.user.phone,
            "penalty_date": row.penalty_date,
            "amount": row.amount,
            "reason": row.reason,
            "status": row.status,
            "created_by": row.created_by.get_full_name() or row.created_by.phone,
            "approved_by": None if row.approved_by is None else (row.approved_by.get_full_name() or row.approved_by.phone),
            "approved_at": row.approved_at,
        } for row in rows[:1000]]
        response = {"penalties": data}
        if has_feature_access(request, "hrms_penalty_manage"):
            response["employees"] = [{
                "id": employee.id,
                "employee_id": employee.employee_id,
                "name": employee.user.get_full_name() or employee.user.phone,
            } for employee in EmployeeProfile.objects.filter(is_active=True).select_related("user")]
        return Response(response)

    def post(self, request):
        if not has_feature_access(request, "hrms_penalty_manage"):
            return Response({"detail": "Penalty management permission is required."}, status=403)
        employee = EmployeeProfile.objects.filter(pk=request.data.get("employee_id"), is_active=True).first()
        if employee is None:
            return Response({"detail": "Active employee is required."}, status=400)
        try:
            penalty_date = date.fromisoformat(request.data.get("penalty_date", ""))
            amount = _money(request.data.get("amount", ""))
        except (ValueError, TypeError, ArithmeticError):
            return Response({"detail": "Valid penalty date and amount are required."}, status=400)
        reason = (request.data.get("reason") or "").strip()
        if amount <= 0 or not reason:
            return Response({"detail": "Amount must be greater than zero and reason is required."}, status=400)
        row = EmployeePenalty.objects.create(
            employee=employee,
            penalty_date=penalty_date,
            amount=amount,
            reason=reason,
            created_by=request.user,
        )
        return Response({"id": row.id, "status": row.status, "detail": "Penalty saved as draft for approval."}, status=201)


class EmployeePenaltyActionAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    @transaction.atomic
    def post(self, request, penalty_id):
        if not has_feature_access(request, "hrms_penalty_manage"):
            return Response({"detail": "Penalty management permission is required."}, status=403)
        row = EmployeePenalty.objects.select_for_update().filter(pk=penalty_id, status="DRAFT").first()
        if row is None:
            return Response({"detail": "Draft penalty not found."}, status=404)
        action = request.data.get("action")
        if action == "APPROVE":
            row.status = "APPROVED"
            row.approved_by = request.user
            row.approved_at = timezone.now()
            row.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        elif action == "CANCEL":
            row.status = "CANCELLED"
            row.cancelled_at = timezone.now()
            row.save(update_fields=["status", "cancelled_at", "updated_at"])
        else:
            return Response({"detail": "Action must be APPROVE or CANCEL."}, status=400)
        return Response({"detail": f"Penalty {row.status.lower()}.", "status": row.status})


class PayrollExcelReportAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    def get(self, request):
        if not has_feature_access(request, "hrms_payroll_manage"):
            return Response({"detail": "Payroll management permission is required."}, status=403)
        try:
            month = _month(request.query_params.get("month", ""))
        except ValueError:
            return Response({"detail": "Month must be YYYY-MM."}, status=400)
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        rows = PayrollRecord.objects.filter(payroll_month=month).select_related("employee__user")
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Salary Register"
        headers = ["Employee ID", "Employee", "Base Salary", "Payable Base", "Late Days", "Late Penalty", "Half-day Deduction", "Absence Deduction", "OT Hours", "OT Amount", "Rent Incentive", "Sale Incentive", "Other Earnings", "Other Deductions", "Net Salary", "Status"]
        sheet.append([f"ARI SMART RO — Salary Register {month:%B %Y}"])
        sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
        sheet["A1"].font = Font(size=16, bold=True, color="FFFFFF")
        sheet["A1"].fill = PatternFill("solid", fgColor="07315E")
        sheet["A1"].alignment = Alignment(horizontal="center")
        sheet.append(headers)
        for cell in sheet[2]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="0868D7")
        for row in rows:
            sheet.append([row.employee.employee_id, row.employee.user.get_full_name(), row.base_salary, row.payable_base, row.late_days, row.late_penalty, row.half_day_deduction, row.absence_deduction, row.overtime_hours, row.overtime_amount, row.rent_incentive, row.sale_incentive, row.other_earnings, row.other_deductions, row.net_salary, row.status])
        sheet.freeze_panes = "A3"
        sheet.auto_filter.ref = f"A2:P{max(2, sheet.max_row)}"
        for column_index in range(1, sheet.max_column + 1):
            letter = get_column_letter(column_index)
            values = (
                sheet.cell(row=row_index, column=column_index).value
                for row_index in range(1, sheet.max_row + 1)
            )
            sheet.column_dimensions[letter].width = min(
                28,
                max(12, max(len(str(value or "")) for value in values) + 2),
            )
        stream = BytesIO()
        workbook.save(stream)
        response = HttpResponse(stream.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="ARI_Salary_Register_{month:%Y_%m}.xlsx"'
        return response


class PerformanceReviewAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    def get(self, request):
        rows = PerformanceReview.objects.select_related(
            "employee__user", "reviewer"
        )
        can_manage = has_feature_access(request, "hrms_performance_manage")
        if not can_manage:
            rows = rows.filter(employee__user=request.user)
        employee_id = request.query_params.get("employee_id")
        if employee_id and can_manage:
            rows = rows.filter(employee_id=employee_id)

        return Response({
            "reviews": [{
                "id": row.id,
                "employee_id": row.employee_id,
                "employee_name": row.employee.user.get_full_name() or row.employee.user.phone,
                "period_start": row.period_start,
                "period_end": row.period_end,
                "reviewer": row.reviewer.get_full_name() or row.reviewer.phone,
                "goals_score": row.goals_score,
                "attendance_score": row.attendance_score,
                "service_quality_score": row.service_quality_score,
                "customer_score": row.customer_score,
                "sales_score": row.sales_score,
                "overall_score": row.overall_score,
                "strengths": row.strengths,
                "improvement_plan": row.improvement_plan,
                "comments": row.comments,
                "status": row.status,
                "finalized_at": row.finalized_at,
                "acknowledged_at": row.acknowledged_at,
            } for row in rows[:500]]
        })

    def post(self, request):
        if not has_feature_access(request, "hrms_performance_manage"):
            return Response({"detail": "Performance management permission is required."}, status=403)

        try:
            employee = EmployeeProfile.objects.get(
                pk=request.data.get("employee_id"),
                is_active=True,
            )
            period_start = date.fromisoformat(str(request.data.get("period_start") or ""))
            period_end = date.fromisoformat(str(request.data.get("period_end") or ""))
        except (EmployeeProfile.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "Valid employee and review period are required."}, status=400)

        if period_end < period_start:
            return Response({"detail": "Review period end cannot be before start."}, status=400)

        score_fields = [
            "goals_score",
            "attendance_score",
            "service_quality_score",
            "customer_score",
            "sales_score",
        ]
        scores = {}
        try:
            for field in score_fields:
                value = Decimal(str(request.data.get(field, 0)))
                if value < 0 or value > 100:
                    return Response({"detail": f"{field} must be between 0 and 100."}, status=400)
                scores[field] = value
        except Exception:
            return Response({"detail": "Performance scores must be numeric."}, status=400)

        row, created = PerformanceReview.objects.get_or_create(
            employee=employee,
            period_start=period_start,
            period_end=period_end,
            defaults={"reviewer": request.user},
        )
        if not created and row.status in {"FINAL", "ACKNOWLEDGED"}:
            return Response({"detail": "Finalized review cannot be edited."}, status=409)

        row.reviewer = request.user
        for field, value in scores.items():
            setattr(row, field, value)
        row.strengths = str(request.data.get("strengths") or "").strip()
        row.improvement_plan = str(request.data.get("improvement_plan") or "").strip()
        row.comments = str(request.data.get("comments") or "").strip()
        row.recalculate()
        row.status = "SUBMITTED"
        row.save()
        return Response({
            "id": row.id,
            "status": row.status,
            "overall_score": row.overall_score,
            "detail": "Performance review saved.",
        }, status=201 if created else 200)


class PerformanceReviewActionAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    def post(self, request, review_id):
        row = PerformanceReview.objects.select_related("employee__user").filter(pk=review_id).first()
        if row is None:
            return Response({"detail": "Performance review not found."}, status=404)

        action = str(request.data.get("action") or "").upper()
        if action == "FINALIZE":
            if not has_feature_access(request, "hrms_performance_manage"):
                return Response({"detail": "Performance management permission is required."}, status=403)
            if row.status not in {"DRAFT", "SUBMITTED"}:
                return Response({"detail": "Only draft/submitted review can be finalized."}, status=400)
            row.status = "FINAL"
            row.finalized_at = timezone.now()
            row.save(update_fields=["status", "finalized_at", "updated_at"])
            return Response({"detail": "Performance review finalized.", "status": row.status})

        if action == "ACKNOWLEDGE":
            if row.employee.user_id != request.user.id:
                return Response({"detail": "Only the employee can acknowledge this review."}, status=403)
            if row.status != "FINAL":
                return Response({"detail": "Only a final review can be acknowledged."}, status=400)
            row.status = "ACKNOWLEDGED"
            row.acknowledged_at = timezone.now()
            row.save(update_fields=["status", "acknowledged_at", "updated_at"])
            return Response({"detail": "Performance review acknowledged.", "status": row.status})

        return Response({"detail": "Action must be FINALIZE or ACKNOWLEDGE."}, status=400)


class EmployeeDocumentComplianceAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    def get(self, request):
        rows = EmployeeDocument.objects.select_related("employee__user")
        can_manage = has_feature_access(request, "hrms_documents_manage")
        if not can_manage:
            rows = rows.filter(employee__user=request.user)
        employee_id = request.query_params.get("employee_id")
        if employee_id and can_manage:
            rows = rows.filter(employee_id=employee_id)

        today = timezone.localdate()
        data = []
        for row in rows[:500]:
            if row.expiry_date is None:
                expiry_state = "NO_EXPIRY"
            elif row.expiry_date < today:
                expiry_state = "EXPIRED"
            elif row.expiry_date <= today + timedelta(days=30):
                expiry_state = "EXPIRING_SOON"
            else:
                expiry_state = "VALID"
            data.append({
                "id": row.id,
                "employee_id": row.employee_id,
                "employee_name": row.employee.user.get_full_name() or row.employee.user.phone,
                "document_type": row.document_type,
                "document_number": row.document_number,
                "expiry_date": row.expiry_date,
                "verified": row.verified,
                "expiry_state": expiry_state,
                "uploaded_at": row.uploaded_at,
            })

        return Response({"documents": data})

    def post(self, request):
        if not has_feature_access(request, "hrms_documents_manage"):
            return Response({"detail": "Document management permission is required."}, status=403)
        employee = EmployeeProfile.objects.filter(pk=request.data.get("employee_id")).first()
        if employee is None:
            return Response({"detail": "Employee not found."}, status=404)
        document_type = str(request.data.get("document_type") or "").strip()
        if not document_type:
            return Response({"detail": "Document type is required."}, status=400)
        expiry_date = None
        raw_expiry = request.data.get("expiry_date")
        if raw_expiry:
            try:
                expiry_date = date.fromisoformat(str(raw_expiry))
            except ValueError:
                return Response({"detail": "Valid expiry date is required."}, status=400)

        row = EmployeeDocument.objects.create(
            employee=employee,
            document_type=document_type[:50],
            document_number=str(request.data.get("document_number") or "").strip()[:100],
            expiry_date=expiry_date,
            verified=bool(request.data.get("verified", False)),
        )
        return Response({"id": row.id, "detail": "Employee document record added."}, status=201)
