from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import Attendance
from .serializers import AttendanceSerializer
from rest_framework.generics import ListAPIView

from employees.models import EmployeeProfile


class CheckInAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        try:

            employee = EmployeeProfile.objects.get(
                user=request.user
            )

        except EmployeeProfile.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "Employee Profile Not Found"
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        today = timezone.localdate()

        attendance = Attendance.objects.filter(
            employee=employee,
            date=today,
        ).first()

        if attendance:

            return Response(
                {
                    "success": False,
                    "message": "Already Checked In"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        attendance = Attendance.objects.create(

            employee=employee,

            date=today,

            check_in=timezone.now(),

            latitude=request.data.get("latitude"),

            longitude=request.data.get("longitude"),

        )

        # ==========================
        # SELFIE
        # ==========================

        if request.FILES.get("selfie"):

            attendance.selfie = request.FILES["selfie"]

        attendance.save()

        return Response(
            {
                "success": True,
                "message": "Check In Successful",
                "attendance": AttendanceSerializer(
                    attendance
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

class CheckOutAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        employee = EmployeeProfile.objects.get(
            user=request.user
        )

        today = timezone.localdate()

        attendance = Attendance.objects.filter(
            employee=employee,
            date=today,
        ).first()

        if not attendance:

            return Response(
                {
                    "message": "Please Check In First."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if attendance.check_out:

            return Response(
                {
                    "message": "Already Checked Out."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        attendance.check_out = timezone.now()

        seconds = (
            attendance.check_out -
            attendance.check_in
        ).total_seconds()

        attendance.working_hours = round(
            seconds / 3600,
            2,
        )

        attendance.save()

        return Response(
            AttendanceSerializer(attendance).data,
            status=status.HTTP_200_OK,
        )   




class TodayAttendanceAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        employee = EmployeeProfile.objects.get(
            user=request.user
        )

        today = timezone.localdate()

        attendance = Attendance.objects.filter(
            employee=employee,
            date=today,
        ).first()

        if not attendance:
            return Response(
                {
                    "message": "No attendance today."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            AttendanceSerializer(attendance).data
        )


class AttendanceHistoryAPIView(ListAPIView):

    permission_classes = [IsAuthenticated]

    serializer_class = AttendanceSerializer

    def get_queryset(self):

        employee = EmployeeProfile.objects.get(
            user=self.request.user
        )

        return Attendance.objects.filter(
            employee=employee
        ).order_by("-date")