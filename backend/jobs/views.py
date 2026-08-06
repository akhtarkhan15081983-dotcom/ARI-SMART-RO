from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Job,JobMedia,JobGPSLog,JobPartUsed,JobSignature
from .serializers import JobSerializer,JobStatusSerializer,JobMediaSerializer,JobGPSLogSerializer,JobPartUsedSerializer,JobSignatureSerializer
from rest_framework import generics
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .services import change_job_status
from .models import JobActivityLog
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from rest_framework.generics import RetrieveAPIView
from inventory.models import EngineerBagItem


class JobViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Job.objects.select_related(
        "customer",
        "engineer__user",
        "ro_asset",
    )

    serializer_class = JobSerializer

    permission_classes = [
        IsAuthenticated,
    ]

class MyJobsAPIView(generics.ListAPIView):

    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Job.objects.select_related(
                "customer",
                "engineer__user",
                "ro_asset",
            )
            .filter(engineer__user=self.request.user)
            .order_by("-scheduled_date")
        )

class JobAcceptAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):

        try:
            job = Job.objects.get(
                pk=pk,
                engineer__user=request.user
            )
        except Job.DoesNotExist:
            return Response(
                {"detail": "Job not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if job.status != "ASSIGNED":
            return Response(
                {
                    "detail": f"Job cannot be accepted because its current status is '{job.status}'."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            change_job_status(job, "ACCEPTED")
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {
                "message": "Job accepted successfully.",
                "job_id": job.job_id,
                "status": job.status,
            },
            status=status.HTTP_200_OK
        )

class JobChangeStatusAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):

        serializer = JobStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            job = Job.objects.get(
                pk=pk,
                engineer__user=request.user
            )
        except Job.DoesNotExist:
            return Response(
                {"detail": "Job not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            change_job_status(
                job,
                serializer.validated_data["status"]
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "message": "Job status updated successfully.",
                "job_id": job.job_id,
                "status": job.status,
            },
            status=status.HTTP_200_OK
        )

class JobMediaUploadAPIView(APIView):

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):

        try:
            job = Job.objects.get(
                pk=pk,
                engineer__user=request.user
            )
        except Job.DoesNotExist:
            return Response(
                {"detail": "Job not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = JobMediaSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(job=job)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

class JobGPSUploadAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):

        try:
            job = Job.objects.get(
                pk=pk,
                engineer__user=request.user
            )
        except Job.DoesNotExist:
            return Response(
                {"detail": "Job not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = JobGPSLogSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(job=job)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

class JobPartUsedAPIView(APIView):

    def post(self, request, pk):

        job = get_object_or_404(Job, pk=pk)

        serializer = JobPartUsedSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        inventory_item = serializer.validated_data["inventory_item"]

        if inventory_item.status != "ISSUED":
            return Response(
                {
                    "error": "Part is not issued to engineer."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        inventory_item.status = "INSTALLED"
        inventory_item.save()

        serializer.save(job=job)
        
        EngineerBagItem.objects.filter(
            inventory_item=inventory_item,
            status="ISSUED",
        ).update(
            status="INSTALLED"
        )

        inventory_item.status = "INSTALLED"
        inventory_item.save()

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

class JobSignatureUploadAPIView(APIView):

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):

        job = get_object_or_404(
            Job,
            pk=pk,
            engineer__user=request.user,
        )

        serializer = JobSignatureSerializer(data=request.data)

        if serializer.is_valid():

            JobSignature.objects.filter(job=job).delete()

            serializer.save(job=job)

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

class JobDetailAPIView(RetrieveAPIView):

    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Job.objects.select_related(
            "customer",
            "engineer__user",
            "ro_asset",
        ).filter(
            engineer__user=self.request.user
        )

