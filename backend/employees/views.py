from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from .models import EmployeeProfile
from .serializers import (
    EmployeeLocationSerializer,
    EmployeeProfileSerializer,
    EmployeeProfileUpdateSerializer,
    AssignmentEmployeeSerializer,
)


class FaceEnrollmentAPIView(APIView):
    """Enroll a real employee reference photo.

    Enrollment is deliberately not auto-verified. A newly captured image is
    marked pending so demo/seed photos can never silently become trusted.
    """

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

        enrollment_photo = request.FILES.get("photo")
        if enrollment_photo is None:
            return Response(
                {"success": False, "message": "Live enrollment photo is required."},
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
        employee.save(
            update_fields=[
                "photo",
                "face_enrolled_at",
                "face_enrollment_verified",
            ]
        )

        return Response(
            {
                "success": True,
                "message": "Real face photo enrolled. Admin verification is pending.",
                "face_enrolled": True,
                "face_enrollment_verified": False,
                "face_enrolled_at": employee.face_enrolled_at,
            },
            status=status.HTTP_200_OK,
        )


class UpdateLiveLocationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            employee = request.user.employee_profile
        except Exception:
            return Response(
                {"error": "Employee profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EmployeeLocationSerializer(
            employee,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save(
                last_location_updated=timezone.now(),
                is_online=True,
            )
            return Response({"message": "Location Updated Successfully"})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EngineerLiveMapAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        engineers = EmployeeProfile.objects.filter(
            designation="ENGINEER",
            is_active=True,
            last_latitude__isnull=False,
            last_longitude__isnull=False,
        ).select_related("user")

        data = []
        for engineer in engineers:
            data.append({
                "id": engineer.id,
                "employee_id": engineer.employee_id,
                "name": engineer.user.get_full_name(),
                "phone": engineer.user.phone,
                "photo": (
                    request.build_absolute_uri(engineer.photo.url)
                    if engineer.photo else None
                ),
                "latitude": engineer.last_latitude,
                "longitude": engineer.last_longitude,
                "updated_at": engineer.last_location_updated,
                "online": engineer.is_online,
            })
        return Response(data)


class EmployeeProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.employee_profile
        except EmployeeProfile.DoesNotExist:
            return Response(
                {"error": "Employee profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EmployeeProfileSerializer(
            profile,
            context={"request": request},
        )
        return Response(serializer.data)

    def put(self, request):
        try:
            profile = request.user.employee_profile
        except EmployeeProfile.DoesNotExist:
            return Response(
                {"error": "Employee profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EmployeeProfileUpdateSerializer(
            profile,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Profile updated successfully.",
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EngineerListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        engineers = EmployeeProfile.objects.filter(
            designation="ENGINEER",
            is_active=True,
        ).select_related("user")

        data = []
        for engineer in engineers:
            data.append({
                "id": engineer.id,
                "employee_id": engineer.employee_id,
                "name": engineer.user.get_full_name() or engineer.user.phone,
                "phone": engineer.user.phone,
            })
        return Response(data)


class AssignmentEmployeeListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employees = EmployeeProfile.objects.filter(
            designation__in=["ENGINEER", "OFFICE"],
            is_active=True,
        ).select_related("user").order_by(
            "designation",
            "user__first_name",
            "user__last_name",
        )

        serializer = AssignmentEmployeeSerializer(employees, many=True)
        return Response(serializer.data)
