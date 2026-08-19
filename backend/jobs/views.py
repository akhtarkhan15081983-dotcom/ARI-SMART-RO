from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated
import random
from .models import (
    Job,
    JobMedia,
    JobGPSLog,
    JobPartUsed,
    JobSignature,
)
from .serializers import (
    JobSerializer,
    JobStatusSerializer,
    JobMediaSerializer,
    JobGPSLogSerializer,
    JobPartUsedSerializer,
    JobSignatureSerializer,
)

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .services import change_job_status
from .models import JobActivityLog
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from rest_framework.generics import RetrieveAPIView
from inventory.models import (
    InventoryItem,
    EngineerBagItem,
    InventoryAuditLog,
)
from django.db.models import Q
from django.db import transaction
from random import randint
import random

from datetime import timedelta




# ============================================================
# JOB VIEWSET
# ============================================================

class JobViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = JobSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

        return Job.objects.select_related(
            "customer",
            "engineer__user",
            "ro_asset",
        ).filter(
            engineer__user=self.request.user,
        )


# ============================================================
# MY JOBS
# ============================================================

class MyJobsAPIView(generics.ListAPIView):

    serializer_class = JobSerializer

    permission_classes = [
        IsAuthenticated
    ]

    def get_queryset(self):

        queryset = Job.objects.select_related(
            "customer",
            "engineer__user",
            "ro_asset",
        ).filter(
            engineer__user=self.request.user
        )

        job_status = self.request.GET.get(
            "status"
        )

        if job_status:

            queryset = queryset.filter(
                status=job_status
            )

        return queryset.order_by(
            "scheduled_date",
            "-priority",
        )


# ============================================================
# ACCEPT JOB
# ============================================================

class JobAcceptAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def post(
        self,
        request,
        pk,
    ):

        try:

            job = Job.objects.get(
                pk=pk,
                engineer__user=request.user,
            )

        except Job.DoesNotExist:

            return Response(
                {
                    "detail":
                        "Job not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if job.status != "ASSIGNED":

            return Response(
                {
                    "detail":
                        "Job cannot be accepted "
                        f"because its current status "
                        f"is '{job.status}'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:

            change_job_status(
                job,
                "ACCEPTED",
            )

        except ValueError as e:

            return Response(
                {
                    "detail": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message":
                    "Job accepted successfully.",
                "job_id":
                    job.job_id,
                "status":
                    job.status,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# CHANGE JOB STATUS
# ============================================================

class JobChangeStatusAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def post(
        self,
        request,
        pk,
    ):

        serializer = JobStatusSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:

            job = Job.objects.get(
                pk=pk,
                engineer__user=request.user,
            )

        except Job.DoesNotExist:

            return Response(
                {
                    "detail":
                        "Job not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:

            change_job_status(
                job,
                serializer.validated_data[
                    "status"
                ],
            )

        except ValueError as e:

            return Response(
                {
                    "detail": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message":
                    "Job status updated successfully.",
                "job_id":
                    job.job_id,
                "status":
                    job.status,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# JOB MEDIA
# ============================================================

class JobMediaUploadAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    def post(
        self,
        request,
        pk,
    ):

        try:

            job = Job.objects.get(
                pk=pk,
                engineer__user=request.user,
            )

        except Job.DoesNotExist:

            return Response(
                {
                    "detail":
                        "Job not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = JobMediaSerializer(
            data=request.data
        )

        if serializer.is_valid():

            serializer.save(
                job=job
            )

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


# ============================================================
# JOB GPS
# ============================================================

class JobGPSUploadAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def post(
        self,
        request,
        pk,
    ):

        try:

            job = Job.objects.get(
                pk=pk,
                engineer__user=request.user,
            )

        except Job.DoesNotExist:

            return Response(
                {
                    "detail":
                        "Job not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = JobGPSLogSerializer(
            data=request.data
        )

        if serializer.is_valid():

            serializer.save(
                job=job
            )

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


# ============================================================
# SECURE JOB PART USED
# ============================================================

class JobPartUsedAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    @transaction.atomic
    def post(
        self,
        request,
        pk,
    ):

        # ----------------------------------------------------
        # LOCK JOB
        # ----------------------------------------------------

        job = get_object_or_404(
            Job.objects.select_for_update(),
            pk=pk,
            engineer__user=request.user,
        )

        # ----------------------------------------------------
        # PARTS CAN ONLY BE USED DURING ACTIVE WORK
        # ----------------------------------------------------

        if job.status != "IN_PROGRESS":

            return Response(
                {
                    "error":
                        "Parts can only be installed "
                        "while the job is IN_PROGRESS."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # VALIDATE REQUEST
        # ----------------------------------------------------

        serializer = JobPartUsedSerializer(
            data=request.data
        )

        if not serializer.is_valid():

            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        requested_inventory = (
            serializer.validated_data[
                "inventory_item"
            ]
        )

        quantity = serializer.validated_data.get(
            "quantity",
            1,
        )

        # ----------------------------------------------------
        # LOCK PHYSICAL INVENTORY ITEM
        # ----------------------------------------------------

        inventory_item = get_object_or_404(
            InventoryItem.objects
            .select_for_update()
            .select_related("part"),
            pk=requested_inventory.pk,
        )

        # ----------------------------------------------------
        # INVENTORY MUST STILL BE ISSUED
        # ----------------------------------------------------

        if inventory_item.status != "ISSUED":

            InventoryAuditLog.objects.create(
                inventory_item=inventory_item,
                engineer=job.engineer,
                performed_by=request.user,
                job=job,
                action="SECURITY_REJECT",
                old_status=inventory_item.status,
                new_status=inventory_item.status,
                serial_number=(
                    inventory_item.serial_number
                    or ""
                ),
                remarks=(
                    "Attempted to use an inventory "
                    "item that was not in ISSUED status."
                ),
            )

            return Response(
                {
                    "error":
                        "This part is not currently "
                        "issued and cannot be installed."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # SERIALIZED PART SECURITY
        # ----------------------------------------------------

        if inventory_item.part.is_serialized:

            if not inventory_item.serial_number:

                InventoryAuditLog.objects.create(
                    inventory_item=inventory_item,
                    engineer=job.engineer,
                    performed_by=request.user,
                    job=job,
                    action="SECURITY_REJECT",
                    old_status=inventory_item.status,
                    new_status=inventory_item.status,
                    remarks=(
                        "Serialized inventory item "
                        "has no serial number."
                    ),
                )

                return Response(
                    {
                        "error":
                            "Serialized part has no "
                            "serial number."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if quantity != 1:

                InventoryAuditLog.objects.create(
                    inventory_item=inventory_item,
                    engineer=job.engineer,
                    performed_by=request.user,
                    job=job,
                    action="SECURITY_REJECT",
                    old_status=inventory_item.status,
                    new_status=inventory_item.status,
                    serial_number=(
                        inventory_item.serial_number
                        or ""
                    ),
                    remarks=(
                        "Attempted to install a "
                        "serialized part with "
                        "quantity other than 1."
                    ),
                )

                return Response(
                    {
                        "error":
                            "Serialized parts can "
                            "only have quantity 1."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # ----------------------------------------------------
        # ENGINEER OWNERSHIP
        # ----------------------------------------------------

        bag_item = (
            EngineerBagItem.objects
            .select_for_update()
            .filter(
                inventory_item=inventory_item,
                engineer=job.engineer,
                engineer__user=request.user,
                status="ISSUED",
            )
            .first()
        )

        if not bag_item:

            InventoryAuditLog.objects.create(
                inventory_item=inventory_item,
                engineer=job.engineer,
                performed_by=request.user,
                job=job,
                action="SECURITY_REJECT",
                old_status=inventory_item.status,
                new_status=inventory_item.status,
                serial_number=(
                    inventory_item.serial_number
                    or ""
                ),
                remarks=(
                    "Engineer attempted to use a "
                    "part that is not issued to them."
                ),
            )

            return Response(
                {
                    "error":
                        "This part is not issued "
                        "to this engineer."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # SAME PHYSICAL ITEM CANNOT BE USED TWICE
        # ----------------------------------------------------

        existing_usage = (
            JobPartUsed.objects
            .select_for_update()
            .filter(
                inventory_item=inventory_item
            )
            .exclude(
                job=job
            )
            .first()
        )

        if existing_usage:

            InventoryAuditLog.objects.create(
                inventory_item=inventory_item,
                engineer=job.engineer,
                performed_by=request.user,
                job=job,
                action="SECURITY_REJECT",
                old_status=inventory_item.status,
                new_status=inventory_item.status,
                serial_number=(
                    inventory_item.serial_number
                    or ""
                ),
                remarks=(
                    "Physical inventory item is "
                    "already linked to another job: "
                    f"{existing_usage.job.job_id}"
                ),
            )

            return Response(
                {
                    "error":
                        "This physical part has "
                        "already been used on another job."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # SAME PART CANNOT BE SCANNED TWICE ON SAME JOB
        # ----------------------------------------------------

        if JobPartUsed.objects.filter(
            job=job,
            inventory_item=inventory_item,
        ).exists():

            return Response(
                {
                    "error":
                        "This part is already added "
                        "to this job."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # CREATE JOB USAGE RECORD
        # ----------------------------------------------------

        usage = serializer.save(
            job=job
        )

        # ----------------------------------------------------
        # INVENTORY -> INSTALLED
        # ----------------------------------------------------

        old_inventory_status = (
            inventory_item.status
        )

        inventory_item.status = "INSTALLED"

        inventory_item.save(
            update_fields=["status"]
        )

        # ----------------------------------------------------
        # ENGINEER BAG -> INSTALLED
        # ----------------------------------------------------

        bag_item.status = "INSTALLED"

        bag_item.install_date = timezone.now()

        bag_item.save(
            update_fields=[
                "status",
                "install_date",
            ]
        )

        # ----------------------------------------------------
        # AUDIT TRAIL
        # ----------------------------------------------------

        InventoryAuditLog.objects.create(
            inventory_item=inventory_item,
            engineer=job.engineer,
            performed_by=request.user,
            job=job,
            action="INSTALLED",
            old_status=old_inventory_status,
            new_status="INSTALLED",
            serial_number=(
                inventory_item.serial_number
                or ""
            ),
            remarks=(
                usage.remarks
                or ""
            ),
        )

        # ----------------------------------------------------
        # JOB ACTIVITY
        # ----------------------------------------------------

        JobActivityLog.objects.create(
            job=job,
            engineer=job.engineer,
            activity="Part Installed",
            remarks=(
                f"Part: "
                f"{inventory_item.part.name}; "
                f"Code: "
                f"{inventory_item.part.code}; "
                f"Serial: "
                f"{inventory_item.serial_number or 'N/A'}; "
                f"Quantity: {usage.quantity}"
            ),
        )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return Response(
            JobPartUsedSerializer(
                usage
            ).data,
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# JOB SIGNATURE
# ============================================================

class JobSignatureUploadAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    def post(
        self,
        request,
        pk,
    ):

        job = get_object_or_404(
            Job,
            pk=pk,
            engineer__user=request.user,
        )

        serializer = JobSignatureSerializer(
            data=request.data
        )

        if serializer.is_valid():

            JobSignature.objects.filter(
                job=job
            ).delete()

            serializer.save(
                job=job
            )

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


# ============================================================
# JOB DETAIL
# ============================================================

class JobDetailAPIView(
    RetrieveAPIView
):

    serializer_class = JobSerializer

    permission_classes = [
        IsAuthenticated
    ]

    def get_queryset(self):

        return Job.objects.select_related(
            "customer",
            "engineer__user",
            "ro_asset",
        ).filter(
            engineer__user=self.request.user
        )


# ============================================================
# JOB SEARCH
# ============================================================

class JobSearchAPIView(
    generics.ListAPIView
):

    serializer_class = JobSerializer

    permission_classes = [
        IsAuthenticated
    ]

    def get_queryset(self):

        keyword = self.request.GET.get(
            "q",
            "",
        )

        queryset = Job.objects.select_related(
            "customer",
            "engineer__user",
            "ro_asset",
        ).filter(
            engineer__user=self.request.user
        )

        if keyword:

            queryset = queryset.filter(

                Q(
                    job_id__icontains=keyword
                )

                |

                Q(
                    customer__name__icontains=keyword
                )

                |

                Q(
                    customer__phone__icontains=keyword
                )

                |

                Q(
                    customer__card_number__icontains=keyword
                )

            )

        return queryset.order_by(
            "-scheduled_date"
        )


# ============================================================
# GENERATE OTP
# ============================================================

class GenerateOTPAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    OTP_VALIDITY_MINUTES = 5

    def post(self, request, pk):

        job = get_object_or_404(
            Job,
            id=pk,
            engineer__user=request.user,
        )

        otp = str(
            random.randint(
                100000,
                999999,
            )
        )

        now = timezone.now()

        job.customer_otp = otp
        job.otp_verified = False
        job.otp_created_at = now
        job.otp_attempts = 0

        job.save(
            update_fields=[
                "customer_otp",
                "otp_verified",
                "otp_created_at",
                "otp_attempts",
                "updated_at",
            ]
        )

        # IMPORTANT:
        # OTP must NEVER be returned through API.

        return Response(
            {
                "success": True,
                "message": (
                    "Customer OTP generated successfully."
                ),
            },
            status=status.HTTP_200_OK,
        )

# ============================================================
# VERIFY OTP
# ============================================================

class VerifyOTPAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    OTP_VALIDITY_MINUTES = 5
    MAX_OTP_ATTEMPTS = 5

    @transaction.atomic
    def post(
        self,
        request,
        pk,
    ):

        # ----------------------------------------------------
        # LOCK JOB ROW
        # ----------------------------------------------------

        job = get_object_or_404(
            Job.objects.select_for_update(),
            pk=pk,
            engineer__user=request.user,
        )

        # ----------------------------------------------------
        # ALREADY VERIFIED
        # ----------------------------------------------------

        if job.otp_verified:

            return Response(
                {
                    "success": False,
                    "message": "OTP has already been verified.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # OTP MUST EXIST
        # ----------------------------------------------------

        if not job.customer_otp:

            return Response(
                {
                    "success": False,
                    "message": "No active OTP exists for this job.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # OTP CREATION TIME MUST EXIST
        # ----------------------------------------------------

        if not job.otp_created_at:

            return Response(
                {
                    "success": False,
                    "message": "OTP is invalid or expired.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # MAX ATTEMPTS
        # ----------------------------------------------------

        if job.otp_attempts >= self.MAX_OTP_ATTEMPTS:

            job.customer_otp = None
            job.otp_created_at = None
            job.otp_attempts = 0

            job.save(
                update_fields=[
                    "customer_otp",
                    "otp_created_at",
                    "otp_attempts",
                    "updated_at",
                ]
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "OTP verification limit exceeded. "
                        "Please generate a new OTP."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # EXPIRY CHECK
        # ----------------------------------------------------

        expires_at = (
            job.otp_created_at
            + timedelta(
                minutes=self.OTP_VALIDITY_MINUTES
            )
        )

        if timezone.now() >= expires_at:

            job.customer_otp = None
            job.otp_created_at = None
            job.otp_attempts = 0

            job.save(
                update_fields=[
                    "customer_otp",
                    "otp_created_at",
                    "otp_attempts",
                    "updated_at",
                ]
            )

            return Response(
                {
                    "success": False,
                    "message": "OTP has expired. Please generate a new OTP.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # READ OTP
        # ----------------------------------------------------

        otp = request.data.get("otp")

        if otp is None:

            otp = ""

        otp = str(otp).strip()

        # ----------------------------------------------------
        # BASIC OTP FORMAT VALIDATION
        # ----------------------------------------------------

        if (
            len(otp) != 6
            or not otp.isdigit()
        ):

            job.otp_attempts += 1

            job.save(
                update_fields=[
                    "otp_attempts",
                    "updated_at",
                ]
            )

            return Response(
                {
                    "success": False,
                    "message": "Invalid OTP",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # OTP COMPARISON
        # ----------------------------------------------------

        if otp != job.customer_otp:

            job.otp_attempts += 1

            # Invalidate after fifth failed attempt.
            if job.otp_attempts >= self.MAX_OTP_ATTEMPTS:

                job.customer_otp = None
                job.otp_created_at = None

                job.save(
                    update_fields=[
                        "customer_otp",
                        "otp_created_at",
                        "otp_attempts",
                        "updated_at",
                    ]
                )

                return Response(
                    {
                        "success": False,
                        "message": (
                            "OTP verification limit exceeded. "
                            "Please generate a new OTP."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            job.save(
                update_fields=[
                    "otp_attempts",
                    "updated_at",
                ]
            )

            return Response(
                {
                    "success": False,
                    "message": "Invalid OTP",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        job.otp_verified = True

        # OTP should not remain reusable after verification.
        job.customer_otp = None
        job.otp_created_at = None

        job.save(
            update_fields=[
                "otp_verified",
                "customer_otp",
                "otp_created_at",
                "updated_at",
            ]
        )

        return Response(
            {
                "success": True,
                "message": "OTP Verified",
            },
            status=status.HTTP_200_OK,
        )