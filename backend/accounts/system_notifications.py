from decimal import Decimal

from django.db.models import F, Q
from django.utils import timezone

from .models import CustomerEngagement, UserNotification


def upsert_notification(
    user,
    event_key,
    title,
    message,
    category="GENERAL",
    priority="NORMAL",
    action="NONE",
    action_label="",
    valid_until=None,
    metadata=None,
):
    if not user or not user.is_active:
        return None
    row, _ = UserNotification.objects.update_or_create(
        user=user,
        event_key=event_key,
        defaults={
            "title": title[:140],
            "message": message[:1000],
            "category": category,
            "priority": priority,
            "action": action,
            "action_label": action_label[:50],
            "valid_until": valid_until,
            "metadata": metadata or {},
        },
    )
    return row


def _sync_employee(user):
    profile = getattr(user, "employee_profile", None)
    if profile is None:
        return

    from employees.training import sync_training_assignments
    sync_training_assignments(profile)

    from employees.models import LeaveRequest, PayrollRecord
    from jobs.models import Job

    for leave in LeaveRequest.objects.filter(employee=profile).order_by("-created_at")[:12]:
        if leave.status == "PENDING":
            title = "Leave request submitted"
            message = f"{leave.get_leave_type_display()} leave for {leave.start_date:%d %b %Y} is awaiting review."
            priority = "NORMAL"
        elif leave.status == "APPROVED":
            title = "Leave approved"
            message = f"Your leave for {leave.start_date:%d %b %Y} has been approved."
            priority = "HIGH"
        elif leave.status == "REJECTED":
            title = "Leave request rejected"
            message = f"Your leave for {leave.start_date:%d %b %Y} was rejected."
            priority = "HIGH"
        else:
            continue
        upsert_notification(
            user,
            f"leave:{leave.id}:{leave.status}",
            title,
            message,
            category="LEAVE",
            priority=priority,
            action="NOTIFICATIONS",
        )

    for payroll in PayrollRecord.objects.filter(employee=profile).exclude(status="DRAFT").order_by("-payroll_month")[:6]:
        if payroll.status == "APPROVED":
            title = "Salary approved"
            message = f"Payroll for {payroll.payroll_month:%b %Y} is approved. Net salary ₹{payroll.net_salary}."
        else:
            title = "Salary paid"
            message = f"Payroll for {payroll.payroll_month:%b %Y} is marked paid. Net salary ₹{payroll.net_salary}."
        upsert_notification(
            user,
            f"payroll:{payroll.id}:{payroll.status}",
            title,
            message,
            category="PAYROLL",
            priority="HIGH",
            action="NOTIFICATIONS",
        )

    active_statuses = ["ASSIGNED", "ACCEPTED", "ON_THE_WAY", "ARRIVED", "IN_PROGRESS"]
    for job in Job.objects.filter(engineer=profile, status__in=active_statuses).select_related("customer").order_by("-updated_at")[:20]:
        upsert_notification(
            user,
            f"job:{job.id}:{job.status}",
            f"{job.get_job_type_display()} job • {job.status.replace('_', ' ').title()}",
            f"{job.customer.name} • {job.scheduled_date:%d %b %Y %I:%M %p}",
            category="JOB",
            priority="HIGH" if job.priority == "HIGH" else "NORMAL",
            action="NONE",
            metadata={"job_id": job.id, "job_code": job.job_id},
        )


def _sync_customer(user):
    customer = getattr(user, "customer_profile", None)
    if customer is None:
        from customers.models import Customer
        customer = Customer.objects.filter(phone=user.phone, is_active=True).order_by("id").first()
    if customer is None:
        return

    from customers.models import CustomerRentHistory
    from customers.rent_policy import rent_due_date, rent_penalty
    from jobs.models import Job

    today = timezone.localdate()
    current_month = today.replace(day=1)
    outstanding = CustomerRentHistory.objects.filter(
        customer=customer,
        rent_month__lte=current_month,
        paid_amount__lt=F("expected_rent"),
    ).order_by("rent_month")

    if outstanding.exists():
        balance = sum(
            (max(Decimal("0"), row.expected_rent - row.paid_amount) for row in outstanding),
            Decimal("0"),
        )
        penalty = Decimal("0")
        for row in outstanding:
            penalty += rent_penalty(
                max(Decimal("0"), row.expected_rent - row.paid_amount),
                rent_due_date(customer, row.rent_month),
                today,
            )["penalty_amount"]
        due = rent_due_date(customer, current_month)
        overdue = due < today
        title = "Rent overdue" if overdue else "Rent payment reminder"
        total = balance + penalty
        message = (
            f"₹{total.quantize(Decimal('1'))} is payable"
            + (f" including ₹{penalty.quantize(Decimal('1'))} late penalty." if penalty else f" by {due:%d %b}.")
        )
        upsert_notification(
            user,
            f"rent:{customer.id}:{current_month.isoformat()}:{'overdue' if overdue else 'due'}",
            title,
            message,
            category="RENT",
            priority="CRITICAL" if overdue else "HIGH",
            action="RENT",
            action_label="PAY / VIEW RENT",
            metadata={"customer_id": customer.id},
        )

    now = timezone.now()
    offers = CustomerEngagement.objects.filter(
        is_active=True,
        kind="OFFER",
        valid_from__lte=now,
    ).filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=now)
    ).filter(
        Q(audience="ALL", target_user__isnull=True)
        | Q(audience="TARGETED", target_user=user)
    )[:20]
    for offer in offers:
        upsert_notification(
            user,
            f"offer:{offer.id}",
            offer.title,
            offer.message,
            category="OFFER",
            priority="HIGH" if offer.priority >= 75 else "NORMAL",
            action=offer.action,
            action_label=offer.action_label,
            valid_until=offer.valid_until,
            metadata={
                "offer_id": offer.id,
                "promo_code": offer.promo_code,
                "offer_scope": offer.offer_scope,
                "discount_type": offer.discount_type,
                "discount_value": str(offer.discount_value),
            },
        )

    for job in Job.objects.filter(customer=customer).exclude(status__in=["CANCELLED"]).order_by("-updated_at")[:12]:
        upsert_notification(
            user,
            f"customer-job:{job.id}:{job.status}",
            f"{job.get_job_type_display()} update",
            f"Your request/job {job.job_id} is {job.status.replace('_', ' ').lower()}.",
            category="SERVICE" if job.job_type == "SERVICE" else ("COMPLAINT" if job.job_type == "COMPLAINT" else "JOB"),
            priority="HIGH" if job.status in {"ON_THE_WAY", "ARRIVED"} else "NORMAL",
            action="SERVICE" if job.job_type == "SERVICE" else "NONE",
            metadata={"job_id": job.id, "job_code": job.job_id},
        )


def _sync_admin(user):
    if str(getattr(user, "role", "")).upper() != "ADMIN":
        return
    from employees.models import LeaveRequest, PayrollRecord, EmployeePenalty, PerformanceReview
    pending_leave = LeaveRequest.objects.filter(status="PENDING").count()
    draft_payroll = PayrollRecord.objects.filter(status="DRAFT").count()
    draft_penalty = EmployeePenalty.objects.filter(status="DRAFT").count()
    pending_review = PerformanceReview.objects.exclude(status__in=["FINAL", "ACKNOWLEDGED"]).count()
    total = pending_leave + draft_payroll + draft_penalty + pending_review
    if total:
        today = timezone.localdate().isoformat()
        upsert_notification(
            user,
            f"admin-hr-summary:{today}",
            "HR approvals need attention",
            (
                f"{pending_leave} leave • {draft_payroll} payroll • "
                f"{draft_penalty} penalty • {pending_review} performance review pending."
            ),
            category="HRMS",
            priority="HIGH",
            action="NONE",
        )


def sync_system_notifications(user):
    role = str(getattr(user, "role", "") or "").upper()
    if role == "CUSTOMER":
        _sync_customer(user)
    else:
        _sync_employee(user)
    _sync_admin(user)
