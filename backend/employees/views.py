from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from accounts.permissions import IsAdmin, IsOperationsUser, IsStaffOperator

from .models import EmployeeProfile
from .serializers import (
    EmployeeLocationSerializer,
    EmployeeProfileSerializer,
    EmployeeProfileUpdateSerializer,
    AssignmentEmployeeSerializer,
)


class FaceEnrollmentAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            employee = request.user.employee_profile
        except EmployeeProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "Employee profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # First-ever enrollment is allowed. Once a face/device exists, only an
        # explicit admin authorization can open one re-enrollment attempt.
        already_enrolled = bool(employee.face_enrolled_at or employee.attendance_device_id)
        if already_enrolled and not employee.face_enrollment_allowed:
            return Response(
                {
                    "success": False,
                    "message": "Face/device re-enrollment is locked. Ask an admin to allow it.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        enrollment_photo = request.FILES.get("photo")
        device_id = (request.data.get("device_id") or "").strip()

        if enrollment_photo is None:
            return Response(
                {"success": False, "message": "Live enrollment photo is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not device_id or len(device_id) > 128:
            return Response(
                {"success": False, "message": "Valid attendance device ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if enrollment_photo.content_type not in {"image/jpeg", "image/png"}:
            return Response(
                {"success": False, "message": "Enrollment photo must be JPEG or PNG."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if enrollment_photo.size > 5 * 1024 * 1024:
            return Response(
                {"success": False, "message": "Enrollment photo must be 5 MB or smaller."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        employee.photo = enrollment_photo
        employee.face_enrolled_at = timezone.now()
        employee.face_enrollment_verified = False
        employee.attendance_device_id = device_id
        employee.face_enrollment_allowed = False
        employee.save(update_fields=[
            "photo",
            "face_enrolled_at",
            "face_enrollment_verified",
            "attendance_device_id",
            "face_enrollment_allowed",
        ])

        return Response({
            "success": True,
            "message": "Real enrollment photo saved and this device is bound for attendance.",
            "face_enrolled": True,
            "face_enrollment_verified": False,
            "face_enrollment_allowed": False,
            "face_enrolled_at": employee.face_enrolled_at,
            "device_bound": True,
        })


class AdminFaceEnrollmentControlAPIView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, employee_id):
        if getattr(request.user, "role", "") != "ADMIN":
            return Response(
                {"success": False, "message": "Only an admin can control face enrollment."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            employee = EmployeeProfile.objects.select_related("user").get(id=employee_id)
        except EmployeeProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "Employee not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        action = (request.data.get("action") or "").strip().lower()
        if action == "allow_reenrollment":
            employee.face_enrollment_allowed = True
            employee.save(update_fields=["face_enrollment_allowed"])
            return Response({
                "success": True,
                "message": "One face/device re-enrollment has been authorized by admin.",
                "face_enrollment_allowed": True,
            })

        if action == "cancel_reenrollment":
            employee.face_enrollment_allowed = False
            employee.save(update_fields=["face_enrollment_allowed"])
            return Response({
                "success": True,
                "message": "Face/device re-enrollment authorization cancelled.",
                "face_enrollment_allowed": False,
            })

        return Response(
            {"success": False, "message": "Invalid action."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class UpdateLiveLocationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            employee = request.user.employee_profile
        except Exception:
            return Response({"error": "Employee profile not found."}, status=404)

        serializer = EmployeeLocationSerializer(employee, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(last_location_updated=timezone.now(), is_online=True)
            return Response({"message": "Location Updated Successfully"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EngineerLiveMapAPIView(APIView):
    permission_classes = [IsOperationsUser]

    def get(self, request):
        engineers = EmployeeProfile.objects.filter(
            designation="ENGINEER", is_active=True,
            last_latitude__isnull=False, last_longitude__isnull=False,
        ).select_related("user")
        return Response([{
            "id": e.id,
            "employee_id": e.employee_id,
            "name": e.user.get_full_name(),
            "phone": e.user.phone,
            "photo": request.build_absolute_uri(e.photo.url) if e.photo else None,
            "latitude": e.last_latitude,
            "longitude": e.last_longitude,
            "updated_at": e.last_location_updated,
            "online": e.is_online,
        } for e in engineers])


class EmployeeProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.employee_profile
        except EmployeeProfile.DoesNotExist:
            return Response({"error": "Employee profile not found."}, status=404)
        serializer = EmployeeProfileSerializer(profile, context={"request": request})
        data = dict(serializer.data)
        data["face_enrolled"] = profile.face_enrolled_at is not None
        data["face_enrollment_verified"] = profile.face_enrollment_verified
        data["face_enrollment_allowed"] = profile.face_enrollment_allowed
        data["attendance_device_bound"] = bool(profile.attendance_device_id)
        return Response(data)

    def put(self, request):
        try:
            profile = request.user.employee_profile
        except EmployeeProfile.DoesNotExist:
            return Response({"error": "Employee profile not found."}, status=404)
        serializer = EmployeeProfileUpdateSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "message": "Profile updated successfully."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EngineerListAPIView(APIView):
    permission_classes = [IsStaffOperator]

    def get(self, request):
        engineers = EmployeeProfile.objects.filter(
            designation="ENGINEER", is_active=True,
        ).select_related("user")
        return Response([{
            "id": e.id,
            "employee_id": e.employee_id,
            "name": e.user.get_full_name() or e.user.phone,
            "phone": e.user.phone,
            "face_enrolled": e.face_enrolled_at is not None,
            "face_enrollment_verified": e.face_enrollment_verified,
            "face_enrollment_allowed": e.face_enrollment_allowed,
            "attendance_device_bound": bool(e.attendance_device_id),
        } for e in engineers])


class AssignmentEmployeeListAPIView(APIView):
    permission_classes = [IsStaffOperator]

    def get(self, request):
        employees = EmployeeProfile.objects.filter(
            designation__in=["ENGINEER", "OFFICE"], is_active=True,
        ).select_related("user").order_by(
            "designation", "user__first_name", "user__last_name",
        )
        return Response(AssignmentEmployeeSerializer(employees, many=True).data)
