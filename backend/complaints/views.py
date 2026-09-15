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


def restrict_complaints_for_user(queryset, user):
    """
    Apply complaint visibility at the database layer.

    ADMIN / MANAGER / OFFICE:
        Operational roles can see all complaints.

    ENGINEER:
        Can see and work only complaints assigned to that engineer.

    CUSTOMER:
        Can see only their own complaints.
    """
    role = getattr(user, "role", None)

    if role in {"ADMIN", "MANAGER", "OFFICE"}:
        return queryset

    if role == "ENGINEER":
        return queryset.filter(engineer__user=user)

    if role == "CUSTOMER":
        customer = get_logged_in_customer(user)
        if customer is None:
            return queryset.none()
        return queryset.filter(customer=customer)

    return queryset.none()


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

        return restrict_complaints_for_user(
            queryset,
            self.request.user,
        )


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
                latitude=customer.latitude,
                longitude=customer.longitude,
            )

            return

        # ----------------------------------------------------
        # ENGINEER CREATION
        # ----------------------------------------------------
        # An engineer may create a complaint only for a customer assigned
        # to that engineer. The complaint is automatically assigned back
        # to the logged-in engineer.
        # ----------------------------------------------------

        if getattr(self.request.user, "role", None) == "ENGINEER":
            from rest_framework.exceptions import ValidationError

            customer = serializer.validated_data.get("customer")
            employee = getattr(self.request.user, "employee_profile", None)

            if (
                customer is None
                or employee is None
                or customer.assigned_engineer_id != employee.id
            ):
                raise ValidationError({
                    "customer": [
                        "You can create complaints only for customers assigned to you."
                    ]
                })

            location = {}
            if serializer.validated_data.get("latitude") is None:
                location["latitude"] = customer.latitude
            if serializer.validated_data.get("longitude") is None:
                location["longitude"] = customer.longitude

            serializer.save(engineer=employee, **location)
            return

        # ----------------------------------------------------
        # ADMIN / MANAGER / OFFICE CREATION
        # ----------------------------------------------------

        customer = serializer.validated_data.get("customer")
        location = {}
        if customer is not None:
            if serializer.validated_data.get("latitude") is None:
                location["latitude"] = customer.latitude
            if serializer.validated_data.get("longitude") is None:
                location["longitude"] = customer.longitude
        serializer.save(**location)


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

        return restrict_complaints_for_user(
            queryset,
            self.request.user,
        )


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

        role = getattr(self.request.user, "role", None)
        if role == "CUSTOMER":
            return Complaint.objects.none()

        return restrict_complaints_for_user(
            queryset,
            self.request.user,
        )


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

        # Only operational staff may assign / reassign engineers.
        if getattr(request.user, "role", None) not in {"ADMIN", "MANAGER", "OFFICE"}:
            return Response(
                {
                    "success": False,
                    "message": "Only Admin, Manager or Office staff can assign engineers.",
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

            complaint = restrict_complaints_for_user(
                Complaint.objects.all(),
                request.user,
            ).get(pk=pk)

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

            complaint = restrict_complaints_for_user(
                Complaint.objects.all(),
                request.user,
            ).get(pk=pk)

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

            complaint = restrict_complaints_for_user(
                Complaint.objects.all(),
                request.user,
            ).get(pk=pk)

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

        queryset = restrict_complaints_for_user(
            queryset,
            self.request.user,
        )

        if not keyword:
            return queryset.order_by("-id")

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