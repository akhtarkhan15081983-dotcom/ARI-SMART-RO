import calendar
from datetime import date, datetime, time

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import user_role
from complaints.models import Complaint
from customers.models import Customer, CustomerRentHistory
from employees.models import EmployeeProfile
from .models import Job, WorkScheduleOverride


ALLOWED_ROLES = {"ADMIN", "MANAGER", "OFFICE", "ENGINEER"}


def month_bounds(value):
    try:
        year, month = (int(part) for part in value.split("-"))
        first = date(year, month, 1)
    except (AttributeError, TypeError, ValueError):
        raise ValueError("month must use YYYY-MM format")
    return first, date(year, month, calendar.monthrange(year, month)[1])


def aware(day, hour=9):
    return timezone.make_aware(
        datetime.combine(day, time(hour=hour)),
        timezone.get_current_timezone(),
    )


def employee_data(employee):
    return {
        "id": employee.id,
        "employee_id": employee.employee_id,
        "name": employee.user.get_full_name().strip() or employee.user.phone,
    }


def customer_data(customer, latitude=None, longitude=None):
    lat = latitude if latitude is not None else customer.latitude
    lng = longitude if longitude is not None else customer.longitude
    return {
        "id": customer.id,
        "customer_id": customer.customer_id,
        "name": customer.name,
        "phone": customer.phone,
        "alternate_phone": customer.alternate_phone,
        "address": customer.address,
        "area": customer.area,
        "city": customer.city,
        "pincode": customer.pincode,
        "latitude": str(lat) if lat is not None else None,
        "longitude": str(lng) if lng is not None else None,
    }


class WorkPlannerMixin:
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if user_role(request.user) not in ALLOWED_ROLES:
            self.permission_denied(
                request,
                message="Work planner is available to operations staff only.",
            )

    def selected_employee(self, request):
        if user_role(request.user) == "ENGINEER":
            return getattr(request.user, "employee_profile", None)
        employee_id = request.query_params.get("employee_id") or request.data.get("employee_id")
        if employee_id:
            return EmployeeProfile.objects.filter(pk=employee_id, is_active=True).first()
        return None


class WorkCalendarAPIView(WorkPlannerMixin, APIView):
    def get(self, request):
        try:
            first, last = month_bounds(request.query_params.get("month"))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        role = user_role(request.user)
        selected = self.selected_employee(request)
        if role == "ENGINEER" and selected is None:
            return Response({"detail": "Employee profile not found."}, status=status.HTTP_403_FORBIDDEN)

        overrides = {
            row.event_key: row
            for row in WorkScheduleOverride.objects.select_related("employee__user").all()
        }
        moved_jobs = [int(key.split(":")[1]) for key in overrides if key.startswith("JOB:")]
        moved_complaints = [int(key.split(":")[1]) for key in overrides if key.startswith("COMPLAINT:")]

        jobs = Job.objects.select_related("customer", "engineer__user").filter(
            scheduled_date__date__range=(first, last)
        ).exclude(status__in=["COMPLETED", "CANCELLED"]) | Job.objects.select_related(
            "customer", "engineer__user"
        ).filter(id__in=moved_jobs).exclude(status__in=["COMPLETED", "CANCELLED"])
        complaints = Complaint.objects.select_related("customer", "engineer__user").filter(
            scheduled_date__date__range=(first, last), engineer__isnull=False
        ).exclude(status__in=["RESOLVED", "CLOSED", "CANCELLED"]) | Complaint.objects.select_related(
            "customer", "engineer__user"
        ).filter(id__in=moved_complaints).exclude(
            status__in=["RESOLVED", "CLOSED", "CANCELLED"]
        )
        customers = Customer.objects.select_related("assigned_engineer__user").filter(
            is_active=True,
            monthly_rent__gt=0,
            installation_date__isnull=False,
            assigned_engineer__isnull=False,
        )
        if selected:
            jobs = jobs.filter(engineer=selected)
            complaints = complaints.filter(engineer=selected)
            customers = customers.filter(assigned_engineer=selected)

        events = []

        def add(key, kind, title, scheduled, employee, customer, work_status,
                priority="NORMAL", amount=None, detail_id=None, latitude=None, longitude=None):
            override = overrides.get(key)
            if override:
                scheduled, employee = override.scheduled_date, override.employee
            if not first <= scheduled.date() <= last:
                return
            if selected and employee.id != selected.id:
                return
            events.append({
                "key": key,
                "type": kind,
                "title": title,
                "scheduled_at": scheduled.isoformat(),
                "date": scheduled.date().isoformat(),
                "status": work_status,
                "priority": priority,
                "amount": str(amount) if amount is not None else None,
                "detail_id": detail_id,
                "employee": employee_data(employee),
                "customer": customer_data(customer, latitude, longitude),
                "rescheduled": override is not None,
                "reschedule_reason": override.reason if override else "",
            })

        for job in jobs.distinct():
            add(f"JOB:{job.id}", "JOB", job.get_job_type_display(), job.scheduled_date,
                job.engineer, job.customer, job.status, job.priority, detail_id=job.id)
        for complaint in complaints.distinct():
            add(f"COMPLAINT:{complaint.id}", "COMPLAINT", complaint.get_complaint_type_display(),
                complaint.scheduled_date, complaint.engineer, complaint.customer, complaint.status,
                complaint.priority, detail_id=complaint.id,
                latitude=complaint.latitude, longitude=complaint.longitude)

        rent_rows = {
            row.customer_id: row
            for row in CustomerRentHistory.objects.filter(
                customer__in=customers,
                rent_month__year=first.year,
                rent_month__month=first.month,
            )
        }
        for customer in customers:
            day = min(customer.installation_date.day, calendar.monthrange(first.year, first.month)[1])
            key = f"RENT:{customer.id}:{first:%Y-%m}"
            row = rent_rows.get(customer.id)
            expected = row.expected_rent if row else customer.monthly_rent
            paid = row.paid_amount if row else 0
            rent_status = "PAID" if paid >= expected else "PARTIAL" if paid > 0 else "PENDING"
            if rent_status == "PAID":
                continue
            add(key, "RENT", "Rent Collection", aware(date(first.year, first.month, day)),
                customer.assigned_engineer, customer, rent_status,
                amount=max(expected - paid, 0), detail_id=customer.id)

        current_rent_keys = {row["key"] for row in events if row["type"] == "RENT"}
        for key, override in overrides.items():
            if not key.startswith("RENT:") or key in current_rent_keys:
                continue
            if not first <= override.scheduled_date.date() <= last:
                continue
            try:
                customer_id = int(key.split(":")[1])
                rent_year, rent_month = (
                    int(value) for value in key.split(":")[2].split("-")
                )
            except (IndexError, ValueError):
                continue
            customer = Customer.objects.select_related("assigned_engineer__user").filter(
                pk=customer_id, is_active=True
            ).first()
            if customer is None or (selected and override.employee_id != selected.id):
                continue
            rent_row = CustomerRentHistory.objects.filter(
                customer_id=customer_id,
                rent_month__year=rent_year,
                rent_month__month=rent_month,
            ).first()
            expected = rent_row.expected_rent if rent_row else customer.monthly_rent
            paid = rent_row.paid_amount if rent_row else 0
            if paid >= expected:
                continue
            add(key, "RENT", "Rent Collection", override.scheduled_date,
                override.employee, customer, "PENDING",
                amount=max(expected - paid, 0), detail_id=customer.id)

        employees = EmployeeProfile.objects.select_related("user").filter(
            is_active=True, designation="ENGINEER"
        ).order_by("user__first_name", "employee_id")
        return Response({
            "month": first.strftime("%Y-%m"),
            "employees": [employee_data(row) for row in employees] if role != "ENGINEER" else [employee_data(selected)],
            "events": sorted(events, key=lambda row: (row["scheduled_at"], row["customer"]["name"])),
        })


class WorkRescheduleAPIView(WorkPlannerMixin, APIView):
    def patch(self, request):
        key = str(request.data.get("event_key") or "").strip().upper()
        raw_date = request.data.get("scheduled_at")
        try:
            scheduled = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "event_key and a valid scheduled_at are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not key:
            return Response({"detail": "event_key is required."}, status=status.HTTP_400_BAD_REQUEST)
        if timezone.is_naive(scheduled):
            scheduled = timezone.make_aware(scheduled, timezone.get_current_timezone())

        source_employee_id = None
        if key.startswith("JOB:"):
            source_employee_id = Job.objects.filter(pk=key.split(":")[1]).values_list("engineer_id", flat=True).first()
        elif key.startswith("COMPLAINT:"):
            source_employee_id = Complaint.objects.filter(pk=key.split(":")[1]).values_list("engineer_id", flat=True).first()
        elif key.startswith("RENT:"):
            source_employee_id = Customer.objects.filter(pk=key.split(":")[1]).values_list("assigned_engineer_id", flat=True).first()
        if source_employee_id is None:
            return Response({"detail": "Work item not found or not assigned."}, status=status.HTTP_404_NOT_FOUND)

        existing = WorkScheduleOverride.objects.filter(event_key=key).first()
        effective_employee_id = existing.employee_id if existing else source_employee_id
        if user_role(request.user) == "ENGINEER":
            employee = self.selected_employee(request)
            if employee is None or effective_employee_id != employee.id:
                return Response({"detail": "You can only reschedule your own work."}, status=status.HTTP_403_FORBIDDEN)
        else:
            target_id = request.data.get("employee_id") or effective_employee_id
            employee = EmployeeProfile.objects.filter(
                pk=target_id, is_active=True, designation="ENGINEER"
            ).first()
            if employee is None:
                return Response({"detail": "Active engineer not found."}, status=status.HTTP_400_BAD_REQUEST)

        override, _ = WorkScheduleOverride.objects.update_or_create(
            event_key=key,
            defaults={
                "scheduled_date": scheduled,
                "employee": employee,
                "previous_date": existing.scheduled_date if existing else None,
                "reason": str(request.data.get("reason") or "").strip(),
                "updated_by": request.user,
            },
        )
        return Response({
            "message": "Work schedule updated.",
            "event_key": key,
            "scheduled_at": override.scheduled_date.isoformat(),
            "employee": employee_data(employee),
        })


class WorkRouteAPIView(WorkPlannerMixin, APIView):
    def get(self, request):
        try:
            selected_date = date.fromisoformat(request.query_params.get("date"))
        except (TypeError, ValueError):
            return Response({"detail": "date must use YYYY-MM-DD format"}, status=status.HTTP_400_BAD_REQUEST)

        query = request.GET.copy()
        query["month"] = selected_date.strftime("%Y-%m")
        request._request.GET = query
        calendar_response = WorkCalendarAPIView().get(request)
        if calendar_response.status_code != 200:
            return calendar_response
        events = [row for row in calendar_response.data["events"] if row["date"] == selected_date.isoformat()]
        stops = [row for row in events if row["customer"]["latitude"] and row["customer"]["longitude"]]
        for index, row in enumerate(stops, start=1):
            row["sequence"] = index
        return Response({
            "date": selected_date.isoformat(),
            "stops": stops,
            "missing_location_count": len(events) - len(stops),
            "total_work_count": len(events),
        })
