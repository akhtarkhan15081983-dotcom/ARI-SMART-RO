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
