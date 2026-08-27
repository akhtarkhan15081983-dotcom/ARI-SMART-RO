from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView

from .models import Attendance
from .serializers import AttendanceSerializer
from .security import (
    OFFICE_LATITUDE,
    OFFICE_LONGITUDE,
    OFFICE_RADIUS_METERS,
    distance_from_office_meters,
    is_inside_office_geofence,
)
from employees.models import EmployeeProfile


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

        if employee.face_enrolled_at is None or not employee.attendance_device_id:
            return Response(
                {"success": False, "message": "Complete real face/device enrollment before attendance."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not device_id or device_id != employee.attendance_device_id:
            return Response(
                {"success": False, "message": "Attendance is allowed only from the enrolled device."},
                status=status.HTTP_403_FORBIDDEN,
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

        today = timezone.localdate()
        if Attendance.objects.filter(employee=employee, date=today).exists():
            return Response({"success": False, "message": "Already Checked In"}, status=400)

        attendance = Attendance.objects.create(
            employee=employee,
            date=today,
            check_in=timezone.now(),
            latitude=latitude,
            longitude=longitude,
            selfie=selfie,
            identity_review_status="PENDING",
        )
        return Response({
            "success": True,
            "message": "Check In Successful",
            "distance_from_office_meters": round(distance_meters, 1),
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
        attendance.check_out = timezone.now()
        seconds = (attendance.check_out - attendance.check_in).total_seconds()
        attendance.working_hours = round(seconds / 3600, 2)
        attendance.save()
        return Response(AttendanceSerializer(attendance).data)


class TodayAttendanceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = EmployeeProfile.objects.get(user=request.user)
        attendance = Attendance.objects.filter(employee=employee, date=timezone.localdate()).first()
        if not attendance:
            return Response({"message": "No attendance today."}, status=404)
        return Response(AttendanceSerializer(attendance).data)


class AttendanceHistoryAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        employee = EmployeeProfile.objects.get(user=self.request.user)
        return Attendance.objects.filter(employee=employee).order_by("-date")


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

        return Response({
            "success": True,
            "message": f"Attendance selfie review marked {new_status.lower()}.",
            "identity_review_status": new_status,
        })
