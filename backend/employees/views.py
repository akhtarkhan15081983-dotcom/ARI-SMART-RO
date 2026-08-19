from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import EmployeeProfile
from .serializers import (
    EmployeeLocationSerializer,
    EmployeeProfileSerializer,
    EmployeeProfileUpdateSerializer,
    AssignmentEmployeeSerializer,
)


class UpdateLiveLocationAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("========== LIVE LOCATION ==========")
        print("USER :", request.user)
        print("AUTH :", request.auth)
        print("IS AUTH :", request.user.is_authenticated)

        try:
            employee = request.user.employee_profile
        except Exception:
            return Response(
                {
                    "error": "Employee profile not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        print("REQUEST DATA :", request.data)

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

            print("LOCATION UPDATED")

            return Response(
                {
                    "message": "Location Updated Successfully"
                }
            )

        print("ERROR :", serializer.errors)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


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
                    if engineer.photo
                    else None
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
                {
                    "error": "Employee profile not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EmployeeProfileSerializer(
            profile,
            context={
                "request": request,
            },
        )

        return Response(serializer.data)

    def put(self, request):

        try:
            profile = request.user.employee_profile

        except EmployeeProfile.DoesNotExist:

            return Response(
                {
                    "error": "Employee profile not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EmployeeProfileUpdateSerializer(
            profile,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():

            serializer.save()

            return Response(
                {
                    "success": True,
                    "message": "Profile updated successfully."
                }
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

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

                "name": engineer.user.get_full_name()
                or engineer.user.phone,

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

        serializer = AssignmentEmployeeSerializer(
            employees,
            many=True,
        )

        return Response(serializer.data)

