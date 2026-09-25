from datetime import datetime, time, timedelta
from math import atan2, cos, radians, sin, sqrt

from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import user_role
from attendance.models import Attendance
from complaints.models import Complaint
from jobs.models import Job
from tenancy.models import CompanyMembership

from .location_models import EmployeeLocationPoint
from .models import EmployeeProfile


ALLOWED_VIEWER_ROLES = {"ADMIN", "MANAGER", "OFFICE", "ENGINEER"}
GAP_AFTER = timedelta(minutes=3)


def _company_for(request):
    membership = (
        CompanyMembership.objects.filter(
            user=request.user,
            is_active=True,
            company__is_active=True,
            company__lifecycle_status="ACTIVE",
        )
        .select_related("company")
        .first()
    )
    return membership.company if membership else None


def _distance_m(a_lat, a_lng, b_lat, b_lng):
    earth = 6371000.0
    phi1, phi2 = radians(float(a_lat)), radians(float(b_lat))
    dphi = radians(float(b_lat) - float(a_lat))
    dlambda = radians(float(b_lng) - float(a_lng))
    value = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return earth * 2 * atan2(sqrt(value), sqrt(max(0.0, 1 - value)))


def _customer_payload(customer, latitude=None, longitude=None):
    lat = latitude if latitude is not None else customer.latitude
    lng = longitude if longitude is not None else customer.longitude
    return {
        "id": customer.id,
        "customer_id": customer.customer_id,
        "name": customer.name,
        "phone": customer.phone,
        "address": customer.address,
        "area": customer.area,
        "city": customer.city,
        "pincode": customer.pincode,
        "latitude": str(lat) if lat is not None else None,
        "longitude": str(lng) if lng is not None else None,
    }


class EmployeeDayRouteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = user_role(request.user)
        if role not in ALLOWED_VIEWER_ROLES:
            return Response({"detail": "Employee route history is unavailable for this role."}, status=403)

        raw_date = str(request.query_params.get("date") or "").strip()
        try:
            selected_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            return Response({"detail": "date must use YYYY-MM-DD format."}, status=400)

        company = _company_for(request)
        if company is None:
            return Response({"detail": "Active company workspace not found."}, status=403)

        if role == "ENGINEER":
            employee = EmployeeProfile.objects.filter(
                user=request.user,
                company=company,
                is_active=True,
            ).select_related("user").first()
        else:
            employee_id = request.query_params.get("employee_id")
            if not employee_id:
                return Response({"detail": "employee_id is required."}, status=400)
            employee = EmployeeProfile.objects.filter(
                pk=employee_id,
                company=company,
                is_active=True,
            ).select_related("user").first()

        if employee is None:
            return Response({"detail": "Employee not found."}, status=404)

        tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.combine(selected_date, time.min), tz)
        end = start + timedelta(days=1)

        points = list(
            EmployeeLocationPoint.objects.filter(
                employee=employee,
                captured_at__gte=start,
                captured_at__lt=end,
            ).order_by("captured_at", "id")
        )

        route = []
        gaps = []
        total_distance_m = 0.0
        previous = None
        for point in points:
            route.append({
                "latitude": str(point.latitude),
                "longitude": str(point.longitude),
                "captured_at": point.captured_at.isoformat(),
            })
            if previous is not None:
                total_distance_m += _distance_m(
                    previous.latitude,
                    previous.longitude,
                    point.latitude,
                    point.longitude,
                )
                gap = point.captured_at - previous.captured_at
                if gap > GAP_AFTER:
                    gaps.append({
                        "from": previous.captured_at.isoformat(),
                        "to": point.captured_at.isoformat(),
                        "minutes": round(gap.total_seconds() / 60, 1),
                    })
            previous = point

        attendance = Attendance.objects.filter(
            employee=employee,
            date=selected_date,
        ).first()

        jobs = (
            Job.objects.select_related("customer")
            .filter(engineer=employee)
            .filter(
                Q(scheduled_date__date=selected_date)
                | Q(accepted_at__date=selected_date)
                | Q(on_the_way_at__date=selected_date)
                | Q(arrived_at__date=selected_date)
                | Q(in_progress_at__date=selected_date)
                | Q(completed_at__date=selected_date)
            )
            .distinct()
            .order_by("scheduled_date", "id")
        )
        work_events = [
            {
                "type": "JOB",
                "id": job.id,
                "title": job.get_job_type_display(),
                "status": job.status,
                "scheduled_at": job.scheduled_date.isoformat(),
                "started_at": job.in_progress_at.isoformat() if job.in_progress_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "customer": _customer_payload(job.customer),
            }
            for job in jobs
        ]

        linked_complaint_ids = {job.complaint.id for job in jobs if hasattr(job, "complaint")}
        complaints = (
            Complaint.objects.select_related("customer")
            .filter(engineer=employee, scheduled_date__date=selected_date)
            .exclude(id__in=linked_complaint_ids)
            .order_by("scheduled_date", "id")
        )
        work_events.extend(
            {
                "type": "COMPLAINT",
                "id": complaint.id,
                "title": complaint.get_complaint_type_display(),
                "status": complaint.status,
                "scheduled_at": complaint.scheduled_date.isoformat(),
                "started_at": None,
                "completed_at": None,
                "customer": _customer_payload(
                    complaint.customer,
                    complaint.latitude,
                    complaint.longitude,
                ),
            }
            for complaint in complaints
        )
        work_events.sort(key=lambda item: (item.get("scheduled_at") or "", item["id"]))

        return Response({
            "date": selected_date.isoformat(),
            "employee": {
                "id": employee.id,
                "employee_id": employee.employee_id,
                "name": employee.user.get_full_name() or employee.user.phone,
                "designation": employee.designation,
            },
            "attendance": None if attendance is None else {
                "check_in": attendance.check_in.isoformat() if attendance.check_in else None,
                "check_out": attendance.check_out.isoformat() if attendance.check_out else None,
                "working_hours": str(attendance.working_hours),
                "auto_checked_out": attendance.auto_checked_out,
            },
            "route": route,
            "point_count": len(route),
            "total_distance_km": round(total_distance_m / 1000, 2),
            "gaps": gaps,
            "tracking_complete": len(gaps) == 0 and bool(route),
            "first_location_at": route[0]["captured_at"] if route else None,
            "last_location_at": route[-1]["captured_at"] if route else None,
            "work_events": work_events,
        })
