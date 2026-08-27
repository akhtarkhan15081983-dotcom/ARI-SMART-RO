from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied

from accounts.permissions import IsEngineer, IsOperationsUser, IsStaffOperator, STAFF_ROLES, user_role

from jobs.models import (
    Job,
    JobPartUsed,
    JobActivityLog,
)
from jobs.services import change_job_status

from referrals.models import Referral
from referrals.services import qualify_referral

from .models import (
    InstallationPart,
    Installation,
)
from .serializers import (
    InstallationPartSerializer,
    InstallationSerializer,
)




def _installation_queryset_for(user):
    queryset = Installation.objects.select_related(
        "customer", "engineer", "engineer__user", "ro_asset", "job"
    )
    role = user_role(user)
    if role in STAFF_ROLES:
        return queryset
    if role == "ENGINEER":
        return queryset.filter(engineer__user=user)
    return queryset.none()


# ============================================================
# INSTALLATION LIST
# ============================================================

class InstallationListAPIView(generics.ListAPIView):

    serializer_class = InstallationSerializer

    def get_queryset(self):
        return _installation_queryset_for(self.request.user).order_by("-id")

    permission_classes = [IsOperationsUser]


# ============================================================
# INSTALLATION CREATE
# ============================================================

class InstallationCreateAPIView(generics.CreateAPIView):

    queryset = Installation.objects.all()

    serializer_class = InstallationSerializer

    permission_classes = [IsStaffOperator]


# ============================================================
# INSTALLATION DETAIL
# ============================================================

class InstallationDetailAPIView(
    generics.RetrieveAPIView
):


    serializer_class = InstallationSerializer

    def get_queryset(self):
        return _installation_queryset_for(self.request.user)

    permission_classes = [IsOperationsUser]


# ============================================================
# INSTALLATION UPDATE
# ============================================================

class InstallationUpdateAPIView(
    generics.UpdateAPIView
):


    serializer_class = InstallationSerializer

    def get_queryset(self):
        return _installation_queryset_for(self.request.user)

    permission_classes = [IsOperationsUser]


# ============================================================
# INSTALLATION PART CREATE
# ============================================================

class InstallationPartCreateAPIView(
    generics.CreateAPIView
):

    queryset = InstallationPart.objects.all()

    serializer_class = InstallationPartSerializer

    permission_classes = [IsOperationsUser]

    def perform_create(self, serializer):
        installation = serializer.validated_data["installation"]
        if user_role(self.request.user) == "ENGINEER" and installation.engineer.user_id != self.request.user.id:
            raise PermissionDenied("You can add parts only to your assigned installation.")
        serializer.save()


# ============================================================
# COMPLETE INSTALLATION
# ============================================================

class CompleteInstallationAPIView(
    generics.CreateAPIView
):

    serializer_class = InstallationSerializer

    permission_classes = [IsEngineer]

    @transaction.atomic
    def create(
        self,
        request,
        *args,
        **kwargs,
    ):

        # ====================================================
        # GET JOB
        # ====================================================

        job = get_object_or_404(
            Job,
            id=request.data["job"],
            engineer__user=request.user,
        )

        # ====================================================
        # SERIALIZE INSTALLATION DATA
        # ====================================================

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        # ====================================================
        # PREVENT DUPLICATE INSTALLATION
        # ====================================================

        if Installation.objects.filter(
            job=job
        ).exists():

            return Response(
                {
                    "success": False,
                    "message":
                        "Installation already exists for this job.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ====================================================
        # CREATE INSTALLATION
        # ====================================================

        installation = serializer.save(

            job=job,

            customer=job.customer,

            engineer=job.engineer,

            ro_asset=job.ro_asset,

            business_type="RENT",

            scheduled_date=job.scheduled_date,

            status="IN_PROGRESS",
        )

        # ====================================================
        # COPY SCANNED PARTS
        # ====================================================

        parts = (
            JobPartUsed.objects
            .filter(
                job=job
            )
            .select_related(
                "inventory_item",
                "inventory_item__part",
            )
        )

        for part in parts:

            InstallationPart.objects.get_or_create(

                installation=installation,

                inventory_item=part.inventory_item,

                defaults={

                    "part":
                        part.inventory_item.part,

                    "serial_number":
                        part.inventory_item.serial_number,

                    "quantity":
                        part.quantity,
                },
            )

        # ====================================================
        # ACTIVITY LOG
        # ====================================================

        JobActivityLog.objects.create(

            job=job,

            engineer=job.engineer,

            activity="Installation Details Saved",

            remarks=request.data.get(
                "remarks",
                "",
            ),
        )

        # ====================================================
        # COMPLETE JOB
        #
        # IMPORTANT:
        # Existing job workflow is used.
        #
        # This preserves all existing completion checks:
        #
        # 1. Parts scanned
        # 2. Installation exists
        # 3. After Photo exists
        # 4. Customer OTP verified
        # 5. Customer signature exists
        # ====================================================

        if job.status != "COMPLETED":

            try:

                change_job_status(
                    job,
                    "COMPLETED",
                )

            except ValueError as e:

                # --------------------------------------------
                # TRANSACTION ROLLBACK
                #
                # Installation and copied parts will also
                # rollback if completion requirements fail.
                # --------------------------------------------

                return Response(
                    {
                        "success": False,
                        "message": str(e),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # ====================================================
        # REFRESH JOB
        # ====================================================

        job.refresh_from_db()

        # ====================================================
        # VERIFY SUCCESSFUL INSTALLATION
        # ====================================================

        if job.status != "COMPLETED":

            return Response(
                {
                    "success": False,
                    "message":
                        "Installation could not be completed.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ====================================================
        # REFERRAL QUALIFICATION
        #
        # IMPORTANT BUSINESS RULE:
        #
        # Referral reward is created ONLY after
        # successful installation.
        #
        # No successful installation
        #       ↓
        # No referral reward
        # ====================================================

        referred_user = getattr(
            job.customer,
            "user",
            None,
        )

        if referred_user is not None:

            pending_referral = (
                Referral.objects
                .select_for_update()
                .filter(
                    referred_user=referred_user,
                    status="PENDING",
                )
                .first()
            )

            if pending_referral:

                # --------------------------------------------
                # DETERMINE CUSTOMER TYPE
                #
                # monthly_rent > 0
                #       → RENT
                #
                # monthly_rent <= 0
                #       → PURCHASE
                # --------------------------------------------

                monthly_rent = Decimal(
                    str(
                        job.customer.monthly_rent
                        or 0
                    )
                )

                if monthly_rent > 0:

                    referred_type = "RENT"

                else:

                    referred_type = "PURCHASE"

                # --------------------------------------------
                # QUALIFY REFERRAL
                #
                # qualify_referral() creates the reward
                # according to referral business rules.
                # --------------------------------------------

                qualify_referral(

                    pending_referral.id,

                    referred_type=referred_type,

                    qualifying_amount=monthly_rent,

                    actor=request.user,
                )

        # ====================================================
        # FINAL RESPONSE
        # ====================================================

        return Response(
            {
                "success": True,

                "installation_id":
                    installation.installation_id,

                "job_id":
                    job.job_id,

                "job_status":
                    job.status,

                "completed_at":
                    job.completed_at,

                "message":
                    "Installation completed successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# INSTALLATION SEARCH
# ============================================================

class InstallationSearchAPIView(
    generics.ListAPIView
):

    serializer_class = InstallationSerializer

    permission_classes = [IsOperationsUser]

    def get_queryset(self):

        keyword = self.request.GET.get(
            "q",
            "",
        ).strip()

        queryset = _installation_queryset_for(self.request.user)

        if keyword:

            queryset = queryset.filter(

                Q(
                    installation_id__icontains=
                    keyword
                )

                |

                Q(
                    customer__name__icontains=
                    keyword
                )

                |

                Q(
                    customer__phone__icontains=
                    keyword
                )

                |

                Q(
                    customer__card_number__icontains=
                    keyword
                )
            )

        return queryset.order_by(
            "-id"
        )


# ============================================================
# INSTALLATION DASHBOARD
# ============================================================

class InstallationDashboardAPIView(
    APIView
):

    permission_classes = [IsEngineer]

    def get(
        self,
        request,
    ):

        # ====================================================
        # ENGINEER PROFILE
        # ====================================================

        try:

            engineer = request.user.employee_profile

        except AttributeError:

            return Response(
                {
                    "success": False,
                    "message":
                        "Employee profile not found.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ====================================================
        # ENGINEER INSTALLATIONS
        # ====================================================

        queryset = Installation.objects.filter(
            engineer=engineer
        )

        today = timezone.localdate()

        # ====================================================
        # DASHBOARD DATA
        # ====================================================

        data = {

            "success": True,

            "total":
                queryset.count(),

            "scheduled":
                queryset.filter(
                    status="SCHEDULED"
                ).count(),

            "in_progress":
                queryset.filter(
                    status="IN_PROGRESS"
                ).count(),

            "completed":
                queryset.filter(
                    status="COMPLETED"
                ).count(),

            "today":
                queryset.filter(
                    scheduled_date__date=today
                ).count(),
        }

        return Response(
            data
        )