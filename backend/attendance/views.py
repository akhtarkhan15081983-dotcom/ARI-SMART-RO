from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView

from .models import Attendance, AttendanceDeviceOverride, OvertimeRequest
from .work_hours import (
    recalculate_attendance,
    reconcile_open_attendance,
    regular_shift_end,
    overtime_payload,
)
from .serializers import AttendanceSerializer
from .security import (
    OFFICE_LATITUDE,
    OFFICE_LONGITUDE,
    OFFICE_RADIUS_METERS,
    distance_from_office_meters,
    is_inside_office_geofence,
)
from employees.models import EmployeeProfile, HRPolicy
from accounts.audit import write_audit_event
from tenancy.access import request_company


def _is_admin(user):
    return getattr(user, "role", "") == "ADMIN"


def _absolute_file_url(request, file_field):
    if not file_field:
        return None
    try:
        return request.build_absolute_uri(file_field.url)
    except Exception:
        return None


class CheckInAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            employee = EmployeeProfile.objects.get(user=request.user)
        except EmployeeProfile.DoesNotExist:
            return Response({"success": False, "message": "Employee Profile Not Found"}, status=404)

        latitude_raw = request.data.get("latitude")
        longitude_raw = request.data.get("longitude")
        selfie = request.FILES.get("selfie")
        device_id = (request.data.get("device_id") or "").strip()
        today = timezone.localdate()
        emergency_override = AttendanceDeviceOverride.objects.filter(
            employee=employee,
            date=today,
            is_active=True,
        ).first()

        if employee.face_enrolled_at is None or not employee.attendance_device_id:
            return Response(
                {"success": False, "message": "Complete real face/device enrollment before attendance."},
                status=status.HTTP_403_FORBIDDEN,
            )
        device_matches = bool(device_id and device_id == employee.attendance_device_id)
        if not device_matches and emergency_override is None:
            return Response(
                {
                    "success": False,
                    "message": "Attendance is allowed only from the enrolled device. Ask admin for today's emergency device permission if your phone is unavailable.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if not device_id:
            return Response(
                {"success": False, "message": "Valid attendance device ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if latitude_raw in (None, "") or longitude_raw in (None, ""):
            return Response({"success": False, "message": "GPS location is required for attendance."}, status=400)
        if selfie is None:
            return Response({"success": False, "message": "A live selfie is required for attendance."}, status=400)

        try:
            latitude = float(latitude_raw)
            longitude = float(longitude_raw)
        except (TypeError, ValueError):
            return Response({"success": False, "message": "Invalid GPS coordinates."}, status=400)

        distance_meters = distance_from_office_meters(latitude, longitude)
        if not is_inside_office_geofence(latitude, longitude):
            return Response({
                "success": False,
                "message": f"Attendance is allowed only within {int(OFFICE_RADIUS_METERS)}m of the office.",
                "distance_from_office_meters": round(distance_meters, 1),
                "office": {
                    "latitude": OFFICE_LATITUDE,
                    "longitude": OFFICE_LONGITUDE,
                    "radius_meters": OFFICE_RADIUS_METERS,
                },
            }, status=status.HTTP_403_FORBIDDEN)

        if Attendance.objects.filter(employee=employee, date=today).exists():
            return Response({"success": False, "message": "Already Checked In"}, status=400)

        used_override = not device_matches and emergency_override is not None
        remarks = "Admin-approved emergency attendance device override used." if used_override else ""
        attendance = Attendance.objects.create(
            employee=employee,
            date=today,
            check_in=timezone.now(),
            latitude=latitude,
            longitude=longitude,
            selfie=selfie,
            identity_review_status="PENDING",
            remarks=remarks,
        )
        recalculate_attendance(attendance)
        if used_override:
            emergency_override.is_active = False
            emergency_override.save(update_fields=["is_active"])
        return Response({
            "success": True,
            "message": "Check In Successful",
            "distance_from_office_meters": round(distance_meters, 1),
            "device_override_used": used_override,
            "attendance": AttendanceSerializer(attendance).data,
        }, status=status.HTTP_201_CREATED)


class CheckOutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        employee = EmployeeProfile.objects.get(user=request.user)
        today = timezone.localdate()
        attendance = Attendance.objects.filter(employee=employee, date=today).first()
        if not attendance:
            return Response({"message": "Please Check In First."}, status=400)
        if attendance.check_out:
            return Response({"message": "Already Checked Out."}, status=400)
        now = timezone.now()
        shift_end = regular_shift_end(attendance)
        if shift_end and now >= shift_end:
            attendance.check_out = shift_end
            attendance.auto_checked_out = True
            attendance.checkout_reason = "AUTO_8_HOURS"
        else:
            attendance.check_out = now
            attendance.auto_checked_out = False
            attendance.checkout_reason = "MANUAL"
        attendance.save(update_fields=[
            "check_out",
            "auto_checked_out",
            "checkout_reason",
        ])
        recalculate_attendance(attendance, now=now)
        return Response(AttendanceSerializer(attendance).data)


class TodayAttendanceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = EmployeeProfile.objects.get(user=request.user)
        reconcile_open_attendance(employee=employee)
        attendance = Attendance.objects.filter(employee=employee, date=timezone.localdate()).first()
        if not attendance:
            return Response({"message": "No attendance today."}, status=404)
        return Response(AttendanceSerializer(attendance).data)



class OvertimeRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = EmployeeProfile.objects.filter(user=request.user).first()
        if employee is None:
            return Response({"detail": "Employee profile not found."}, status=404)
        reconcile_open_attendance(employee=employee)
        attendance = Attendance.objects.filter(
            employee=employee,
            date=timezone.localdate(),
        ).first()
        if attendance is None:
            return Response({"detail": "Check in before requesting overtime."}, status=400)
        return Response({
            "attendance_id": attendance.id,
            "regular_shift_end_at": regular_shift_end(attendance),
            "regular_working_hours": str(attendance.regular_working_hours),
            "working_hours": str(attendance.working_hours),
            "overtime": overtime_payload(attendance),
        })

    def post(self, request):
        employee = EmployeeProfile.objects.filter(user=request.user).first()
        if employee is None:
            return Response({"detail": "Employee profile not found."}, status=404)
        reconcile_open_attendance(employee=employee)
        attendance = Attendance.objects.filter(
            employee=employee,
            date=timezone.localdate(),
            check_in__isnull=False,
        ).first()
        if attendance is None:
            return Response({"detail": "Check in before requesting overtime."}, status=400)

        reason = str(request.data.get("reason") or "").strip()
        try:
            requested_hours = Decimal(str(request.data.get("hours") or "1"))
        except (InvalidOperation, TypeError, ValueError):
            return Response({"detail": "Valid overtime hours are required."}, status=400)
        if not reason:
            return Response({"detail": "Overtime reason is required."}, status=400)
        if requested_hours <= 0 or requested_hours > Decimal("8"):
            return Response({"detail": "Overtime request must be between 0.25 and 8 hours."}, status=400)
        if requested_hours < Decimal("0.25"):
            return Response({"detail": "Minimum overtime request is 15 minutes."}, status=400)

        existing = OvertimeRequest.objects.filter(attendance=attendance).first()
        if existing and existing.status in {"APPROVED", "COMPLETED"}:
            return Response({"detail": "Overtime is already approved/completed for today."}, status=409)

        row, _ = OvertimeRequest.objects.update_or_create(
            attendance=attendance,
            defaults={
                "requested_hours": requested_hours,
                "approved_hours": Decimal("0"),
                "reason": reason,
                "status": "PENDING",
                "reviewed_by": None,
                "reviewed_at": None,
                "review_note": "",
                "started_at": None,
                "planned_end_at": None,
                "ended_at": None,
                "end_reason": "",
            },
        )
        return Response({
            "message": "Overtime request sent to Admin for approval.",
            "overtime": overtime_payload(attendance),
        }, status=201)


class OvertimeStartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        employee = EmployeeProfile.objects.filter(user=request.user).first()
        if employee is None:
            return Response({"detail": "Employee profile not found."}, status=404)
        reconcile_open_attendance(employee=employee)
        attendance = Attendance.objects.filter(
            employee=employee,
            date=timezone.localdate(),
        ).first()
        if attendance is None:
            return Response({"detail": "Attendance record not found."}, status=404)

        overtime = OvertimeRequest.objects.filter(
            attendance=attendance,
            status="APPROVED",
            started_at__isnull=True,
        ).first()
        if overtime is None:
            return Response({"detail": "Admin-approved overtime is required."}, status=403)

        shift_end = regular_shift_end(attendance)
        now = timezone.now()
        if shift_end and now < shift_end:
            return Response(
                {"detail": "Regular 8-hour shift is still active. Overtime starts after regular shift ends."},
                status=400,
            )

        overtime.started_at = now
        overtime.planned_end_at = now + timedelta(hours=float(overtime.approved_hours))
        overtime.save(update_fields=["started_at", "planned_end_at", "updated_at"])
        recalculate_attendance(attendance, now=now)
        return Response({
            "message": "Approved overtime started.",
            "attendance": AttendanceSerializer(attendance).data,
        })


class OvertimeStopAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        employee = EmployeeProfile.objects.filter(user=request.user).first()
        attendance = Attendance.objects.filter(
            employee=employee,
            date=timezone.localdate(),
        ).first() if employee else None
        if attendance is None:
            return Response({"detail": "Attendance record not found."}, status=404)
        overtime = OvertimeRequest.objects.filter(
            attendance=attendance,
            status="APPROVED",
            started_at__isnull=False,
            ended_at__isnull=True,
        ).first()
        if overtime is None:
            return Response({"detail": "No active overtime session."}, status=400)
        now = timezone.now()
        overtime.ended_at = min(now, overtime.planned_end_at or now)
        overtime.end_reason = "MANUAL"
        overtime.status = "COMPLETED"
        overtime.save(update_fields=["ended_at", "end_reason", "status", "updated_at"])
        recalculate_attendance(attendance, now=now)
        return Response({
            "message": "Overtime stopped.",
            "attendance": AttendanceSerializer(attendance).data,
        })


class AdminOvertimeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin(request.user):
            return Response({"detail": "Only Admin can manage overtime."}, status=403)
        reconcile_open_attendance()
        company = request_company(request)
        rows = OvertimeRequest.objects.select_related(
            "attendance__employee__user",
            "attendance__employee__company",
            "reviewed_by",
        )
        if company is not None:
            rows = rows.filter(attendance__employee__company=company)
        status_filter = str(request.query_params.get("status") or "").upper()
        if status_filter in {"PENDING", "APPROVED", "REJECTED", "COMPLETED", "CANCELLED"}:
            rows = rows.filter(status=status_filter)
        return Response([
            {
                "id": row.id,
                "attendance_id": row.attendance_id,
                "date": row.attendance.date,
                "employee_id": row.attendance.employee.employee_id,
                "employee_name": row.attendance.employee.user.get_full_name() or row.attendance.employee.user.phone,
                "designation": row.attendance.employee.designation,
                "regular_hours": str(row.attendance.regular_working_hours),
                "overtime_hours": str(row.attendance.overtime_working_hours),
                "requested_hours": str(row.requested_hours),
                "approved_hours": str(row.approved_hours),
                "reason": row.reason,
                "status": row.status,
                "requested_at": row.requested_at,
                "review_note": row.review_note,
                "reviewed_at": row.reviewed_at,
                "started_at": row.started_at,
                "planned_end_at": row.planned_end_at,
                "ended_at": row.ended_at,
            }
            for row in rows[:500]
        ])

    def post(self, request, request_id=None):
        if not _is_admin(request.user):
            return Response({"detail": "Only Admin can manage overtime."}, status=403)
        row = OvertimeRequest.objects.select_related(
            "attendance__employee__company"
        ).filter(pk=request_id).first()
        if row is None:
            return Response({"detail": "Overtime request not found."}, status=404)
        company = request_company(request)
        if company is not None and row.attendance.employee.company_id != company.id:
            return Response({"detail": "Overtime request not found in this workspace."}, status=404)

        action = str(request.data.get("action") or "").upper()
        note = str(request.data.get("note") or "").strip()[:300]
        before_state = {
            "status": row.status,
            "approved_hours": str(row.approved_hours),
            "review_note": row.review_note,
        }
        if action == "APPROVE":
            try:
                approved_hours = Decimal(str(
                    request.data.get("approved_hours") or row.requested_hours
                ))
            except (InvalidOperation, TypeError, ValueError):
                return Response({"detail": "Valid approved overtime hours are required."}, status=400)
            if approved_hours <= 0 or approved_hours > row.requested_hours:
                return Response(
                    {"detail": "Approved hours must be above zero and cannot exceed requested hours."},
                    status=400,
                )
            row.status = "APPROVED"
            row.approved_hours = approved_hours
        elif action == "REJECT":
            row.status = "REJECTED"
            row.approved_hours = Decimal("0")
        else:
            return Response({"detail": "Action must be APPROVE or REJECT."}, status=400)

        row.reviewed_by = request.user
        row.reviewed_at = timezone.now()
        row.review_note = note
        row.save(update_fields=[
            "status",
            "approved_hours",
            "reviewed_by",
            "reviewed_at",
            "review_note",
            "updated_at",
        ])
        write_audit_event(
            request=request,
            action="OVERTIME_REVIEWED",
            entity_type="OvertimeRequest",
            entity_id=row.id,
            company=company,
            reason=note,
            before_state=before_state,
            after_state={
                "status": row.status,
                "approved_hours": str(row.approved_hours),
                "review_note": row.review_note,
            },
            metadata={
                "attendance_id": row.attendance_id,
                "employee_id": row.attendance.employee.employee_id,
            },
        )
        return Response({
            "message": f"Overtime request {row.status.lower()}.",
            "status": row.status,
            "approved_hours": str(row.approved_hours),
        })


class AttendanceHistoryAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        employee = EmployeeProfile.objects.get(user=self.request.user)
        return Attendance.objects.filter(employee=employee).order_by("-date")


class AdminAttendanceDeviceOverrideAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin(request.user):
            return Response(
                {"success": False, "message": "Only admin can manage emergency attendance device permission."},
                status=status.HTTP_403_FORBIDDEN,
            )
        today = timezone.localdate()
        overrides = {
            item.employee_id: item
            for item in AttendanceDeviceOverride.objects.filter(date=today)
        }
        employees = EmployeeProfile.objects.filter(is_active=True).select_related("user").order_by(
            "designation", "user__first_name", "user__last_name"
        )
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
        if not _is_admin(request.user):
            return Response(
                {"success": False, "message": "Only admin can manage emergency attendance device permission."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if employee_id is None:
            return Response({"success": False, "message": "Employee is required."}, status=400)
        try:
            employee = EmployeeProfile.objects.select_related("user").get(id=employee_id, is_active=True)
        except EmployeeProfile.DoesNotExist:
            return Response({"success": False, "message": "Employee not found."}, status=404)

        action = (request.data.get("action") or "").strip().lower()
        if action not in {"allow_today", "revoke_today"}:
            return Response({"success": False, "message": "Invalid action."}, status=400)

        override, created = AttendanceDeviceOverride.objects.get_or_create(
            employee=employee,
            date=timezone.localdate(),
            defaults={"granted_by": request.user, "is_active": True},
        )
        before_allowed = None if created else override.is_active
        override.is_active = action == "allow_today"
        override.granted_by = request.user
        override.save(update_fields=["is_active", "granted_by"])

        allowed = override.is_active
        write_audit_event(
            request=request,
            action="ATTENDANCE_DEVICE_OVERRIDE_CHANGED",
            entity_type="AttendanceDeviceOverride",
            entity_id=override.id,
            company=getattr(employee, "company", None),
            before_state={"is_active": before_allowed},
            after_state={"is_active": allowed},
            metadata={
                "employee_id": employee.employee_id,
                "date": str(override.date),
            },
        )
        return Response({
            "success": True,
            "message": (
                "Emergency attendance from another phone is allowed for today only."
                if allowed
                else "Today's emergency attendance device permission has been revoked."
            ),
            "employee_id": employee.id,
            "emergency_device_allowed_today": allowed,
            "date": override.date,
        })


class AdminAttendanceReviewListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin(request.user):
            return Response(
                {"success": False, "message": "Only admin can review attendance selfies."},
                status=status.HTTP_403_FORBIDDEN,
            )

        review_status = (request.query_params.get("status") or "PENDING").upper()
        if review_status not in {"PENDING", "APPROVED", "REJECTED", "ALL"}:
            review_status = "PENDING"

        qs = Attendance.objects.select_related("employee__user", "identity_reviewed_by").order_by("-date", "-check_in")
        if review_status != "ALL":
            qs = qs.filter(identity_review_status=review_status)

        data = []
        for attendance in qs[:200]:
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
                    attendance.identity_reviewed_by.get_full_name() or attendance.identity_reviewed_by.phone
                    if attendance.identity_reviewed_by else None
                ),
                "remarks": attendance.remarks,
            })
        return Response(data)


class AdminAttendanceReviewActionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, attendance_id):
        if not _is_admin(request.user):
            return Response(
                {"success": False, "message": "Only admin can review attendance selfies."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            attendance = Attendance.objects.select_related("employee__user").get(id=attendance_id)
        except Attendance.DoesNotExist:
            return Response({"success": False, "message": "Attendance record not found."}, status=404)

        action = (request.data.get("action") or "").strip().lower()
        note = (request.data.get("note") or "").strip()[:255]
        if action == "approve":
            new_status = "APPROVED"
        elif action == "reject":
            new_status = "REJECTED"
        elif action == "pending":
            new_status = "PENDING"
        else:
            return Response({"success": False, "message": "Invalid review action."}, status=400)

        before_state = {
            "identity_review_status": attendance.identity_review_status,
            "identity_review_note": attendance.identity_review_note,
        }
        attendance.identity_review_status = new_status
        attendance.identity_reviewed_by = request.user if new_status != "PENDING" else None
        attendance.identity_reviewed_at = timezone.now() if new_status != "PENDING" else None
        attendance.identity_review_note = note
        attendance.save(update_fields=[
            "identity_review_status",
            "identity_reviewed_by",
            "identity_reviewed_at",
            "identity_review_note",
        ])
        write_audit_event(
            request=request,
            action="ATTENDANCE_IDENTITY_REVIEWED",
            entity_type="Attendance",
            entity_id=attendance.id,
            company=getattr(attendance.employee, "company", None),
            reason=note,
            before_state=before_state,
            after_state={
                "identity_review_status": attendance.identity_review_status,
                "identity_review_note": attendance.identity_review_note,
            },
            metadata={
                "employee_id": attendance.employee.employee_id,
                "date": str(attendance.date),
            },
        )

        return Response({
            "success": True,
            "message": f"Attendance selfie review marked {new_status.lower()}.",
            "identity_review_status": new_status,
        })
