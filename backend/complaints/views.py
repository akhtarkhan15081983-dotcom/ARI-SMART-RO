from django.db.models import Q
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from customers.models import Customer
from .models import Complaint
from .serializers import ComplaintSerializer


# ============================================================
# HELPER
# ============================================================

def get_logged_in_customer(user):
    """
    Customer user ko uske phone number se Customer record
    ke saath match karta hai.
    """

    if not user or not user.is_authenticated:
        return None

    if getattr(user, "role", None) != "CUSTOMER":
        return None

    try:
        return Customer.objects.get(
            phone=user.phone,
            is_active=True,
        )
    except Customer.DoesNotExist:
        return None


# ============================================================
# COMPLAINT LIST
# ============================================================

class ComplaintListAPIView(generics.ListAPIView):

    serializer_class = ComplaintSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

        queryset = (
            Complaint.objects
            .select_related(
                "customer",
                "engineer__user",
                "linked_service",
            )
            .order_by("-id")
        )

        # ----------------------------------------------------
        # CUSTOMER
        # ----------------------------------------------------
        # Customer ko sirf apni complaints dikhengi.
        # ----------------------------------------------------

        if getattr(self.request.user, "role", None) == "CUSTOMER":

            customer = get_logged_in_customer(
                self.request.user
            )

            if customer is None:
                return Complaint.objects.none()

            return queryset.filter(
                customer=customer
            )

        # ----------------------------------------------------
        # STAFF / ENGINEER / ADMIN / MANAGER / OFFICE
        # ----------------------------------------------------

        return queryset


# ============================================================
# CREATE COMPLAINT
# ============================================================

class ComplaintCreateAPIView(generics.CreateAPIView):

    serializer_class = ComplaintSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):
        return Complaint.objects.all()

    def perform_create(self, serializer):

        # ----------------------------------------------------
        # CUSTOMER CREATION
        # ----------------------------------------------------
        # Customer ID Flutter se lene ki zarurat nahi.
        # Backend logged-in user ke phone se customer find karega.
        # ----------------------------------------------------

        if getattr(
            self.request.user,
            "role",
            None,
        ) == "CUSTOMER":

            customer = get_logged_in_customer(
                self.request.user
            )

            if customer is None:
                from rest_framework.exceptions import ValidationError

                raise ValidationError({
                    "customer": [
                        "Customer account is not linked to a customer record."
                    ]
                })

            serializer.save(
                customer=customer,
                engineer=None,
                priority="NORMAL",
            )

            return

        # ----------------------------------------------------
        # STAFF CREATION
        # ----------------------------------------------------
        # Existing staff complaint flow same rahega.
        # Staff customer / engineer select kar sakta hai.
        # ----------------------------------------------------

        serializer.save()


# ============================================================
# COMPLAINT DETAIL
# ============================================================

class ComplaintDetailAPIView(
    generics.RetrieveAPIView
):

    serializer_class = ComplaintSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

        queryset = (
            Complaint.objects
            .select_related(
                "customer",
                "engineer__user",
                "linked_service",
            )
        )

        # Customer sirf apni complaint dekh sakta hai.

        if getattr(
            self.request.user,
            "role",
            None,
        ) == "CUSTOMER":

            customer = get_logged_in_customer(
                self.request.user
            )

            if customer is None:
                return Complaint.objects.none()

            return queryset.filter(
                customer=customer
            )

        return queryset


# ============================================================
# UPDATE COMPLAINT
# ============================================================

class ComplaintUpdateAPIView(
    generics.UpdateAPIView
):

    serializer_class = ComplaintSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

        queryset = Complaint.objects.all()

        # ----------------------------------------------------
        # CUSTOMER
        # ----------------------------------------------------
        # Customer existing complaint ko direct update nahi
        # kar sakta. Isse customer engineer/status/priority
        # manipulate nahi kar payega.
        # ----------------------------------------------------

        if getattr(
            self.request.user,
            "role",
            None,
        ) == "CUSTOMER":

            return Complaint.objects.none()

        return queryset


# ============================================================
# ASSIGN / REASSIGN ENGINEER
# ============================================================

class ComplaintAssignEngineerAPIView(
    APIView
):

    permission_classes = [
        IsAuthenticated,
    ]

    def patch(
        self,
        request,
        pk,
    ):

        # ----------------------------------------------------
        # CUSTOMER NOT ALLOWED
        # ----------------------------------------------------

        if getattr(
            request.user,
            "role",
            None,
        ) == "CUSTOMER":

            return Response(
                {
                    "success": False,
                    "message":
                        "Customers cannot assign engineers.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:

            complaint = (
                Complaint.objects
                .select_related(
                    "customer",
                    "engineer__user",
                )
                .get(pk=pk)
            )

        except Complaint.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message":
                        "Complaint not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        engineer_id = request.data.get(
            "engineer"
        )

        if engineer_id in [
            None,
            "",
        ]:

            return Response(
                {
                    "success": False,
                    "message":
                        "Engineer is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:

            engineer_id = int(
                engineer_id
            )

        except (
            TypeError,
            ValueError,
        ):

            return Response(
                {
                    "success": False,
                    "message":
                        "Invalid engineer ID.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:

            from employees.models import (
                EmployeeProfile
            )

            engineer = (
                EmployeeProfile.objects
                .select_related("user")
                .get(
                    id=engineer_id,
                    is_active=True,
                    designation="ENGINEER",
                )
            )

        except EmployeeProfile.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message":
                        "Active engineer not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        complaint.engineer = engineer

        if complaint.status == "NEW":
            complaint.status = "ASSIGNED"

        complaint.save()

        return Response(
            {
                "success": True,
                "message":
                    "Engineer assigned successfully.",
                "complaint":
                    ComplaintSerializer(
                        complaint
                    ).data,
            },
            status=status.HTTP_200_OK,
        )

# ============================================================
# START COMPLAINT / MARK IN PROGRESS
# ============================================================

class ComplaintStartAPIView(
    APIView
):

    permission_classes = [
        IsAuthenticated,
    ]

    def patch(
        self,
        request,
        pk,
    ):

        # ----------------------------------------------------
        # CUSTOMER NOT ALLOWED
        # ----------------------------------------------------

        if getattr(
            request.user,
            "role",
            None,
        ) == "CUSTOMER":

            return Response(
                {
                    "success": False,
                    "message":
                        "Customers cannot start complaints.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ----------------------------------------------------
        # GET COMPLAINT
        # ----------------------------------------------------

        try:

            complaint = Complaint.objects.get(
                pk=pk
            )

        except Complaint.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message":
                        "Complaint not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ----------------------------------------------------
        # VALID STATUS
        # ----------------------------------------------------

        if complaint.status == "CLOSED":

            return Response(
                {
                    "success": False,
                    "message":
                        "Closed complaints cannot be started.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if complaint.status == "RESOLVED":

            return Response(
                {
                    "success": False,
                    "message":
                        "Resolved complaints cannot be started again.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # ENGINEER CHECK
        # ----------------------------------------------------

        if complaint.engineer is None:

            return Response(
                {
                    "success": False,
                    "message":
                        "Engineer must be assigned before starting.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # MARK IN PROGRESS
        # ----------------------------------------------------

        complaint.status = "IN_PROGRESS"

        complaint.save()

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return Response(
            {
                "success": True,
                "message":
                    "Complaint marked as in progress.",
                "complaint":
                    ComplaintSerializer(
                        complaint
                    ).data,
            },
            status=status.HTTP_200_OK,
        )



# ============================================================
# RESOLVE COMPLAINT
# ============================================================

class ComplaintResolveAPIView(
    APIView
):

    permission_classes = [
        IsAuthenticated,
    ]

    def patch(
        self,
        request,
        pk,
    ):

        # ----------------------------------------------------
        # CUSTOMER NOT ALLOWED
        # ----------------------------------------------------

        if getattr(
            request.user,
            "role",
            None,
        ) == "CUSTOMER":

            return Response(
                {
                    "success": False,
                    "message":
                        "Customers cannot resolve complaints.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:

            complaint = Complaint.objects.get(
                pk=pk
            )

        except Complaint.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message":
                        "Complaint not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        resolution = (
            request.data.get(
                "resolution",
                "",
            )
            or ""
        ).strip()

        engineer_remarks = (
            request.data.get(
                "engineer_remarks",
                "",
            )
            or ""
        ).strip()

        if not resolution:

            return Response(
                {
                    "success": False,
                    "message":
                        "Resolution is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        complaint.resolution = resolution

        if engineer_remarks:

            complaint.engineer_remarks = (
                engineer_remarks
            )

        complaint.status = "RESOLVED"

        complaint.resolved_date = (
            timezone.now()
        )

        complaint.save()

        return Response(
            {
                "success": True,
                "message":
                    "Complaint resolved successfully.",
                "complaint":
                    ComplaintSerializer(
                        complaint
                    ).data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# CLOSE COMPLAINT
# ============================================================

class ComplaintCloseAPIView(
    APIView
):

    permission_classes = [
        IsAuthenticated,
    ]

    def patch(
        self,
        request,
        pk,
    ):

        # ----------------------------------------------------
        # CUSTOMER NOT ALLOWED
        # ----------------------------------------------------

        if getattr(
            request.user,
            "role",
            None,
        ) == "CUSTOMER":

            return Response(
                {
                    "success": False,
                    "message":
                        "Customers cannot close complaints.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:

            complaint = Complaint.objects.get(
                pk=pk
            )

        except Complaint.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message":
                        "Complaint not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if complaint.status not in [
            "RESOLVED",
            "CLOSED",
        ]:

            return Response(
                {
                    "success": False,
                    "message":
                        "Only resolved complaints can be closed.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        complaint.status = "CLOSED"

        if complaint.resolved_date is None:

            complaint.resolved_date = (
                timezone.now()
            )

        complaint.save()

        return Response(
            {
                "success": True,
                "message":
                    "Complaint closed successfully.",
                "complaint":
                    ComplaintSerializer(
                        complaint
                    ).data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# SEARCH COMPLAINTS
# ============================================================

class ComplaintSearchAPIView(
    generics.ListAPIView
):

    serializer_class = ComplaintSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

        keyword = (
            self.request.GET
            .get("q", "")
            .strip()
        )

        queryset = (
            Complaint.objects
            .select_related(
                "customer",
                "engineer__user",
                "linked_service",
            )
        )

        # ----------------------------------------------------
        # CUSTOMER
        # ----------------------------------------------------
        # Customer search bhi sirf apni complaints ke andar.
        # ----------------------------------------------------

        if getattr(
            self.request.user,
            "role",
            None,
        ) == "CUSTOMER":

            customer = get_logged_in_customer(
                self.request.user
            )

            if customer is None:
                return Complaint.objects.none()

            queryset = queryset.filter(
                customer=customer
            )

            # Customer ke liye apni complaint search.
            if not keyword:
                return queryset.order_by("-id")

            queryset = queryset.filter(
                Q(
                    complaint_id__icontains=keyword
                )
                |
                Q(
                    complaint_type__icontains=keyword
                )
                |
                Q(
                    priority__icontains=keyword
                )
                |
                Q(
                    status__icontains=keyword
                )
                |
                Q(
                    description__icontains=keyword
                )
            )

            return queryset.order_by("-id")

        # ----------------------------------------------------
        # STAFF SEARCH
        # ----------------------------------------------------

        if not keyword:

            return queryset.order_by(
                "-id"
            )

        queryset = queryset.filter(
            Q(
                complaint_id__icontains=
                keyword
            )
            |
            Q(
                customer__name__icontains=
                keyword
            )
            |
            Q(
                customer__customer_id__icontains=
                keyword
            )
            |
            Q(
                customer__phone__icontains=
                keyword
            )
            |
            Q(
                customer__alternate_phone__icontains=
                keyword
            )
            |
            Q(
                customer__card_number__icontains=
                keyword
            )
            |
            Q(
                customer__old_card_number__icontains=
                keyword
            )
            |
            Q(
                engineer__employee_id__icontains=
                keyword
            )
            |
            Q(
                complaint_type__icontains=
                keyword
            )
            |
            Q(
                priority__icontains=
                keyword
            )
            |
            Q(
                status__icontains=
                keyword
            )
            |
            Q(
                description__icontains=
                keyword
            )
        )

        return queryset.order_by(
            "-id"
        )