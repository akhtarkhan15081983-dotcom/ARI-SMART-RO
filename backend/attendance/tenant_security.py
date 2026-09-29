from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
from employees.models import EmployeeProfile
from tenancy.access import request_company

from .models import Attendance, AttendanceDeviceOverride
from .views import (
    AdminAttendanceDeviceOverrideAPIView,
    AdminAttendanceReviewActionAPIView,
    _absolute_file_url,
)


class TenantScopedAttendanceDeviceOverrideAPIView(AdminAttendanceDeviceOverrideAPIView):
    """Keep emergency attendance-device permissions inside the admin's company."""

    permission_classes = [IsAdmin]

    def get(self, request):
        company = request_company(request)
        if company is None:
            return Response(
                {"detail": "Active company workspace not found."},
                status=status.HTTP_403_FORBIDDEN,
            )
        today = timezone.localdate()
        employees = EmployeeProfile.objects.filter(
            company=company,
            is_active=True,
            user__is_active=True,
        ).select_related("user").order_by(
            "designation", "user__first_name", "user__last_name"
        )
        overrides = {
            item.employee_id: item
            for item in AttendanceDeviceOverride.objects.filter(
                employee__company=company,
                date=today,
            )
        }
        return Response([
            {
                "id": employee.id,
                "employee_id": employee.employee_id,
                "name": employee.user.get_full_name() or employee.user.phone,
                "phone": employee.user.phone,
                "designation": employee.designation,
                "attendance_device_bound": bool(employee.attendance_device_id),
                "emergency_device_allowed_today": bool(
                    overrides.get(employee.id) and overrides[employee.id].is_active
                ),
            }
            for employee in employees
        ])

    def post(self, request, employee_id=None):
        company = request_company(request)
        if company is None:
            return Response(
                {"detail": "Active company workspace not found."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if employee_id is None:
            return Response(
                {"success": False, "message": "Employee is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not EmployeeProfile.objects.filter(
            pk=employee_id,
            company=company,
            is_active=True,
        ).exists():
            return Response(
                {"success": False, "message": "Employee not found in this workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().post(request, employee_id=employee_id)


class TenantScopedAttendanceReviewListAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        company = request_company(request)
        if company is None:
            return Response(
                {"detail": "Active company workspace not found."},
                status=status.HTTP_403_FORBIDDEN,
            )

        review_status = str(request.query_params.get("status") or "PENDING").upper()
        if review_status not in {"PENDING", "APPROVED", "REJECTED", "ALL"}:
            review_status = "PENDING"

        rows = Attendance.objects.filter(
            employee__company=company,
        ).select_related(
            "employee__user", "identity_reviewed_by"
        ).order_by("-date", "-check_in")
        if review_status != "ALL":
            rows = rows.filter(identity_review_status=review_status)

        data = []
        for attendance in rows[:200]:
            employee = attendance.employee
            data.append({
                "id": attendance.id,
                "employee_id": employee.employee_id,
                "employee_name": employee.user.get_full_name() or employee.user.phone,
                "phone": employee.user.phone,
                "date": attendance.date,
                "check_in": attendance.check_in,
                "distance_note": "GPS already passed server-side office geofence at check-in.",
                "enrollment_photo": _absolute_file_url(request, employee.photo),
                "attendance_selfie": _absolute_file_url(request, attendance.selfie),
                "identity_review_status": attendance.identity_review_status,
                "identity_review_note": attendance.identity_review_note,
                "identity_reviewed_at": attendance.identity_reviewed_at,
                "identity_reviewed_by": (
                    attendance.identity_reviewed_by.get_full_name()
                    or attendance.identity_reviewed_by.phone
                    if attendance.identity_reviewed_by
                    else None
                ),
                "remarks": attendance.remarks,
            })
        return Response(data)


class TenantScopedAttendanceReviewActionAPIView(AdminAttendanceReviewActionAPIView):
    permission_classes = [IsAdmin]

    def post(self, request, attendance_id):
        company = request_company(request)
        if company is None:
            return Response(
                {"detail": "Active company workspace not found."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not Attendance.objects.filter(
            pk=attendance_id,
            employee__company=company,
        ).exists():
            return Response(
                {"success": False, "message": "Attendance record not found in this workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().post(request, attendance_id=attendance_id)
