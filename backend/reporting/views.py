from decimal import Decimal
from io import BytesIO

import openpyxl
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStaffOperator
from attendance.models import Attendance
from complaints.models import Complaint
from customers.models import Customer, CustomerRentHistory, CustomerRentPayment
from installation.models import Installation
from inventory.models import EngineerBagItem, InventoryItem, PartRequest
from jobs.models import Job, JobPartUsed
from purchase.models import PurchaseItem
from service.models import Service

from .periods import resolve_period


ZERO = Decimal("0.00")


def _decimal(value):
    return value if isinstance(value, Decimal) else Decimal(str(value or 0))


def _money(value):
    return f"{_decimal(value):.2f}"


def _datetime_filter(period, field):
    return {
        f"{field}__gte": period.start_datetime,
        f"{field}__lt": period.end_datetime,
    }


def _status_counts(queryset, field="status"):
    return {
        str(row[field] or "UNKNOWN"): row["count"]
        for row in queryset.values(field).annotate(count=Count("id")).order_by(field)
    }


def _employee_name(row, prefix):
    first_name = str(row.get(f"{prefix}__user__first_name") or "").strip()
    last_name = str(row.get(f"{prefix}__user__last_name") or "").strip()
    phone = str(row.get(f"{prefix}__user__phone") or "").strip()
    return f"{first_name} {last_name}".strip() or phone or "Unassigned"


def build_parts_report(period):
    usage = JobPartUsed.objects.filter(
        **_datetime_filter(period, "used_at")
    ).select_related(
        "job__engineer__user",
        "inventory_item__part",
    )

    totals = usage.aggregate(
        entries=Count("id"),
        quantity=Sum("quantity"),
        jobs=Count("job", distinct=True),
        employees=Count("job__engineer", distinct=True),
        parts=Count("inventory_item__part", distinct=True),
    )

    by_employee_rows = usage.values(
        "job__engineer__employee_id",
        "job__engineer__user__first_name",
        "job__engineer__user__last_name",
        "job__engineer__user__phone",
    ).annotate(
        usage_entries=Count("id"),
        quantity=Sum("quantity"),
        jobs=Count("job", distinct=True),
        different_parts=Count("inventory_item__part", distinct=True),
    ).order_by("-quantity", "job__engineer__employee_id")

    by_employee = [
        {
            "employee_id": row["job__engineer__employee_id"],
            "employee_name": _employee_name(row, "job__engineer"),
            "usage_entries": row["usage_entries"],
            "quantity": row["quantity"] or 0,
            "jobs": row["jobs"],
            "different_parts": row["different_parts"],
        }
        for row in by_employee_rows
    ]

    by_part = list(
        usage.values(
            "inventory_item__part__id",
            "inventory_item__part__code",
            "inventory_item__part__name",
        ).annotate(
            usage_entries=Count("id"),
            quantity=Sum("quantity"),
            employees=Count("job__engineer", distinct=True),
            jobs=Count("job", distinct=True),
        ).order_by("-quantity", "inventory_item__part__name")
    )

    recent_usage = [
        {
            "used_at": item.used_at.isoformat(),
            "job_id": item.job.job_id,
            "employee_id": item.job.engineer.employee_id,
            "employee_name": item.job.engineer.user.get_full_name()
            or item.job.engineer.user.phone,
            "part_code": item.inventory_item.part.code,
            "part_name": item.inventory_item.part.name,
            "serial_number": item.inventory_item.serial_number or "",
            "quantity": item.quantity,
            "remarks": item.remarks,
        }
        for item in usage.order_by("-used_at")[:100]
    ]

    bag_issued = EngineerBagItem.objects.filter(
        **_datetime_filter(period, "issue_date")
    ).count()
    bag_installed = EngineerBagItem.objects.filter(
        install_date__isnull=False,
        **_datetime_filter(period, "install_date"),
    ).count()
    bag_returned = EngineerBagItem.objects.filter(
        return_date__isnull=False,
        **_datetime_filter(period, "return_date"),
    ).count()

    requests = PartRequest.objects.filter(
        **_datetime_filter(period, "created_at")
    )

    return {
        "summary": {
            "usage_entries": totals["entries"] or 0,
            "used_quantity": totals["quantity"] or 0,
            "jobs": totals["jobs"] or 0,
            "employees": totals["employees"] or 0,
            "different_parts": totals["parts"] or 0,
            "bag_items_issued": bag_issued,
            "bag_items_installed": bag_installed,
            "bag_items_returned": bag_returned,
            "part_requests": requests.count(),
            "requested_quantity": requests.aggregate(total=Sum("quantity"))["total"] or 0,
        },
        "part_request_status": _status_counts(requests),
        "inventory_snapshot": _status_counts(InventoryItem.objects.all()),
        "by_employee": by_employee,
        "by_part": by_part,
        "recent_usage": recent_usage,
        "recent_usage_limited_to": 100,
    }


def build_rent_report(period):
    history = CustomerRentHistory.objects.filter(
        rent_month__range=(period.start, period.end)
    ).select_related("customer")

    totals = history.aggregate(
        expected=Sum("expected_rent"),
        paid=Sum("paid_amount"),
        customers=Count("customer", distinct=True),
        rent_rows=Count("id"),
    )
    expected = _decimal(totals["expected"])
    paid = _decimal(totals["paid"])

    overdue_rows = history.values(
        "customer__id",
        "customer__customer_id",
        "customer__name",
        "customer__phone",
    ).annotate(
        expected=Sum("expected_rent"),
        paid=Sum("paid_amount"),
    ).order_by("customer__name")

    outstanding_customers = []
    for row in overdue_rows:
        due = max(_decimal(row["expected"]) - _decimal(row["paid"]), ZERO)
        if due > 0:
            outstanding_customers.append({
                "customer_id": row["customer__id"],
                "customer_code": row["customer__customer_id"],
                "customer_name": row["customer__name"],
                "phone": row["customer__phone"],
                "expected": _money(row["expected"]),
                "paid": _money(row["paid"]),
                "outstanding": _money(due),
            })
    outstanding_customers.sort(
        key=lambda row: Decimal(row["outstanding"]),
        reverse=True,
    )

    payments = CustomerRentPayment.objects.filter(
        payment_date__range=(period.start, period.end)
    ).select_related(
        "customer",
        "collected_by__user",
    )
    payment_total = _decimal(payments.aggregate(total=Sum("amount"))["total"])

    by_mode = [
        {
            "payment_mode": row["payment_mode"],
            "payments": row["payments"],
            "amount": _money(row["amount"]),
        }
        for row in payments.values("payment_mode").annotate(
            payments=Count("id"),
            amount=Sum("amount"),
        ).order_by("-amount")
    ]

    collector_rows = payments.values(
        "collected_by__employee_id",
        "collected_by__user__first_name",
        "collected_by__user__last_name",
        "collected_by__user__phone",
    ).annotate(
        payments=Count("id"),
        customers=Count("customer", distinct=True),
        amount=Sum("amount"),
    ).order_by("-amount")

    by_collector = [
        {
            "employee_id": row["collected_by__employee_id"],
            "employee_name": _employee_name(row, "collected_by"),
            "payments": row["payments"],
            "customers": row["customers"],
            "amount": _money(row["amount"]),
        }
        for row in collector_rows
    ]

    efficiency = float((paid / expected * 100).quantize(Decimal("0.01"))) if expected else 0.0

    return {
        "summary": {
            "rent_rows": totals["rent_rows"] or 0,
            "customers": totals["customers"] or 0,
            "expected": _money(expected),
            "paid": _money(paid),
            "outstanding": _money(max(expected - paid, ZERO)),
            "collection_efficiency_percent": efficiency,
            "payment_transactions": payments.count(),
            "payments_received": _money(payment_total),
            "customers_with_due": len(outstanding_customers),
        },
        "by_payment_mode": by_mode,
        "by_collector": by_collector,
        "outstanding_customers": outstanding_customers[:200],
        "outstanding_customers_limited_to": 200,
    }


def build_attendance_report(period):
    attendance = Attendance.objects.filter(
        date__range=(period.start, period.end)
    ).select_related("employee__user")

    totals = attendance.aggregate(
        records=Count("id"),
        employees=Count("employee", distinct=True),
        present=Count("id", filter=Q(status="PRESENT")),
        absent=Count("id", filter=Q(status="ABSENT")),
        half_day=Count("id", filter=Q(status="HALF_DAY")),
        leave=Count("id", filter=Q(status="LEAVE")),
        working_hours=Sum("working_hours"),
        checked_in=Count("id", filter=Q(check_in__isnull=False)),
        checked_out=Count("id", filter=Q(check_out__isnull=False)),
        pending_reviews=Count("id", filter=Q(identity_review_status="PENDING")),
        rejected_reviews=Count("id", filter=Q(identity_review_status="REJECTED")),
    )

    employee_rows = attendance.values(
        "employee__employee_id",
        "employee__user__first_name",
        "employee__user__last_name",
        "employee__user__phone",
        "employee__designation",
    ).annotate(
        records=Count("id"),
        present=Count("id", filter=Q(status="PRESENT")),
        absent=Count("id", filter=Q(status="ABSENT")),
        half_day=Count("id", filter=Q(status="HALF_DAY")),
        leave=Count("id", filter=Q(status="LEAVE")),
        working_hours=Sum("working_hours"),
        late_checkout_missing=Count(
            "id",
            filter=Q(check_in__isnull=False, check_out__isnull=True),
        ),
    ).order_by("employee__employee_id")

    by_employee = [
        {
            "employee_id": row["employee__employee_id"],
            "employee_name": _employee_name(row, "employee"),
            "designation": row["employee__designation"],
            "records": row["records"],
            "present": row["present"],
            "absent": row["absent"],
            "half_day": row["half_day"],
            "leave": row["leave"],
            "working_hours": _money(row["working_hours"]),
            "missing_checkout": row["late_checkout_missing"],
        }
        for row in employee_rows
    ]

    return {
        "summary": {
            "records": totals["records"] or 0,
            "employees": totals["employees"] or 0,
            "present": totals["present"] or 0,
            "absent": totals["absent"] or 0,
            "half_day": totals["half_day"] or 0,
            "leave": totals["leave"] or 0,
            "working_hours": _money(totals["working_hours"]),
            "checked_in": totals["checked_in"] or 0,
            "checked_out": totals["checked_out"] or 0,
            "pending_identity_reviews": totals["pending_reviews"] or 0,
            "rejected_identity_reviews": totals["rejected_reviews"] or 0,
        },
        "by_employee": by_employee,
    }


def build_operations_report(period):
    jobs_created = Job.objects.filter(**_datetime_filter(period, "created_at"))
    jobs_completed = Job.objects.filter(
        completed_at__isnull=False,
        **_datetime_filter(period, "completed_at"),
    )
    complaints_created = Complaint.objects.filter(
        **_datetime_filter(period, "complaint_date")
    )
    complaints_resolved = Complaint.objects.filter(
        resolved_date__isnull=False,
        **_datetime_filter(period, "resolved_date"),
    )
    installations = Installation.objects.filter(
        **_datetime_filter(period, "scheduled_date")
    )
    services = Service.objects.filter(
        **_datetime_filter(period, "scheduled_date")
    )
    new_customers = Customer.objects.filter(
        **_datetime_filter(period, "created_at")
    )

    purchase_value_expression = ExpressionWrapper(
        F("quantity") * F("purchase_price"),
        output_field=DecimalField(max_digits=18, decimal_places=2),
    )
    purchase_items = PurchaseItem.objects.filter(
        purchase__invoice_date__range=(period.start, period.end)
    )
    purchase_totals = purchase_items.aggregate(
        items=Count("id"),
        total_quantity=Sum("quantity"),
        value=Sum(purchase_value_expression),
        invoices=Count("purchase", distinct=True),
        suppliers=Count("purchase__supplier", distinct=True),
    )

    open_complaints = Complaint.objects.exclude(
        status__in=["RESOLVED", "CLOSED", "CANCELLED"]
    ).count()

    return {
        "summary": {
            "new_customers": new_customers.count(),
            "jobs_created": jobs_created.count(),
            "jobs_completed": jobs_completed.count(),
            "complaints_created": complaints_created.count(),
            "complaints_resolved": complaints_resolved.count(),
            "open_complaints_snapshot": open_complaints,
            "installations_scheduled": installations.count(),
            "services_scheduled": services.count(),
            "purchase_invoices": purchase_totals["invoices"] or 0,
            "purchase_suppliers": purchase_totals["suppliers"] or 0,
            "purchase_items": purchase_totals["items"] or 0,
            "purchase_quantity": purchase_totals["total_quantity"] or 0,
            "purchase_value": _money(purchase_totals["value"]),
        },
        "jobs_by_status": _status_counts(jobs_created),
        "jobs_by_type": _status_counts(jobs_created, "job_type"),
        "complaints_by_status": _status_counts(complaints_created),
        "complaints_by_type": _status_counts(complaints_created, "complaint_type"),
        "installations_by_status": _status_counts(installations),
        "services_by_status": _status_counts(services),
    }


def build_reports(period):
    parts = build_parts_report(period)
    rent = build_rent_report(period)
    attendance = build_attendance_report(period)
    operations = build_operations_report(period)

    return {
        "period": period.as_dict(),
        "overview": {
            "parts_used": parts["summary"]["used_quantity"],
            "rent_collected": rent["summary"]["payments_received"],
            "rent_outstanding": rent["summary"]["outstanding"],
            "attendance_hours": attendance["summary"]["working_hours"],
            "jobs_completed": operations["summary"]["jobs_completed"],
            "open_complaints": operations["summary"]["open_complaints_snapshot"],
        },
        "parts": parts,
        "rent": rent,
        "attendance": attendance,
        "operations": operations,
    }


def _append_rows(worksheet, rows):
    if not rows:
        worksheet.append(["No records"])
        return
    headers = list(rows[0].keys())
    worksheet.append(headers)
    for row in rows:
        worksheet.append([row.get(header, "") for header in headers])


def build_workbook(data):
    workbook = openpyxl.Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Summary"
    summary_sheet.append(["ARI SMART RO REPORT"])
    summary_sheet.append(["Period", data["period"]["label"]])
    summary_sheet.append([])
    summary_sheet.append(["Metric", "Value"])
    for key, value in data["overview"].items():
        summary_sheet.append([key.replace("_", " ").title(), value])

    parts_sheet = workbook.create_sheet("Parts by Employee")
    _append_rows(parts_sheet, data["parts"]["by_employee"])

    part_sheet = workbook.create_sheet("Parts by Item")
    _append_rows(part_sheet, data["parts"]["by_part"])

    rent_sheet = workbook.create_sheet("Rent Due")
    _append_rows(rent_sheet, data["rent"]["outstanding_customers"])

    collector_sheet = workbook.create_sheet("Rent Collectors")
    _append_rows(collector_sheet, data["rent"]["by_collector"])

    attendance_sheet = workbook.create_sheet("Attendance")
    _append_rows(attendance_sheet, data["attendance"]["by_employee"])

    operations_sheet = workbook.create_sheet("Operations")
    operations_sheet.append(["Metric", "Value"])
    for key, value in data["operations"]["summary"].items():
        operations_sheet.append([key.replace("_", " ").title(), value])

    for worksheet in workbook.worksheets:
        worksheet.freeze_panes = "A2"
        for column in worksheet.columns:
            width = min(max(len(str(cell.value or "")) for cell in column) + 2, 40)
            worksheet.column_dimensions[column[0].column_letter].width = width

    return workbook


class ReportsSummaryAPIView(APIView):
    permission_classes = [IsStaffOperator]

    def get(self, request):
        try:
            period = resolve_period(request.query_params)
        except ValueError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "success": True,
            **build_reports(period),
        })


class ReportsExportAPIView(APIView):
    permission_classes = [IsStaffOperator]

    def get(self, request):
        try:
            period = resolve_period(request.query_params)
        except ValueError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = build_reports(period)
        workbook = build_workbook(data)
        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        filename = (
            f"ari-smart-ro-{period.key}-"
            f"{period.start.isoformat()}-{period.end.isoformat()}.xlsx"
        )
        response = HttpResponse(
            output.getvalue(),
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
