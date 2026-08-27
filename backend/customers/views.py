from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import (
    IsEngineer,
    IsStaffOperator,
    IsVerifiedCustomer,
    IsVerifiedCustomerOrOperations,
    STAFF_ROLES,
    user_role,
)
from employees.models import EmployeeProfile
from .models import Customer

from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from jobs.models import Job
from jobs.serializers import JobSerializer
from django.utils import timezone
from assets.models import ROAsset
from products.models import ROModel
import random
from .models import CustomerRentHistory
from datetime import date
import calendar
from assets.models.asset import ROAsset
from decimal import Decimal
from django.db import transaction
from .models import CustomerRentHistory, CustomerRentPayment
from referrals.services import claim_welcome_reward

from referrals.services import (
    calculate_max_redeemable,
    redeem_wallet,
)

from .serializers import (
    CustomerSerializer,
    WalkInCustomerSerializer,
    CustomerProfileSerializer,
    MyROSerializer,
)


def _customer_queryset_for(user):
    role = user_role(user)
    queryset = Customer.objects.select_related("assigned_engineer__user")
    if role in STAFF_ROLES:
        return queryset
    if role == "ENGINEER":
        return queryset.filter(assigned_engineer__user=user)
    if role == "CUSTOMER":
        if not user.is_verified or not user.is_active:
            return queryset.none()
        return queryset.filter(phone=user.phone)
    return queryset.none()


class CustomerProfileAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        if request.user.role != "CUSTOMER":

            return Response(
                {
                    "success": False,
                    "message": (
                        "Only customers can access "
                        "this profile."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if not request.user.is_verified:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Please verify your phone number first."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        customer = (
            Customer.objects
            .select_related(
                "user",
                "assigned_engineer__user",
            )
            .filter(
                user=request.user
            )
            .first()
        )

        # ----------------------------------------------------
        # LEGACY CUSTOMER MATCH
        # ----------------------------------------------------
        #
        # Existing imported customers may not yet have
        # user relation. Match them safely by phone.
        # ----------------------------------------------------

        if customer is None:

            customer = (
                Customer.objects
                .select_related(
                    "assigned_engineer__user"
                )
                .filter(
                    phone=request.user.phone,
                    user__isnull=True,
                )
                .first()
            )

            if customer:

                customer.user = request.user

                customer.save(
                    update_fields=[
                        "user"
                    ]
                )

        if customer is None:

            return Response(
                {
                    "success": False,
                    "profile_exists": False,
                    "message": (
                        "Customer profile is not "
                        "created yet."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "success": True,
                "profile_exists": True,
                "profile": CustomerProfileSerializer(
                    customer
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):

        if request.user.role != "CUSTOMER":

            return Response(
                {
                    "success": False,
                    "message": (
                        "Only customers can create "
                        "this profile."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if not request.user.is_verified:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Please verify your phone number first."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        existing_customer = (
            Customer.objects
            .filter(
                user=request.user
            )
            .first()
        )

        if existing_customer:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Customer profile already exists."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # CHECK LEGACY CUSTOMER BY PHONE
        # ----------------------------------------------------

        legacy_customer = (
            Customer.objects
            .filter(
                phone=request.user.phone,
                user__isnull=True,
            )
            .first()
        )

        if legacy_customer:

            with transaction.atomic():

                legacy_customer.user = request.user

                legacy_customer.save(
                    update_fields=[
                        "user"
                    ]
                )

                claim_welcome_reward(
                    request.user
                )

            return Response(
                {
                    "success": True,
                    "message": (
                        "Existing customer profile "
                        "linked successfully."
                    ),
                    "profile": CustomerProfileSerializer(
                        legacy_customer
                    ).data,
                },
                status=status.HTTP_200_OK,
            )

        # ----------------------------------------------------
        # CREATE NEW CUSTOMER PROFILE
        # ----------------------------------------------------

        serializer = CustomerProfileSerializer(
            data=request.data
        )

        if not serializer.is_valid():

            return Response(
                {
                    "success": False,
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():

            customer = serializer.save(
                user=request.user,
                phone=request.user.phone,
            )

            claim_welcome_reward(
                request.user
            )

        return Response(
            {
                "success": True,
                "message": (
                    "Customer profile created successfully."
                ),
                "profile": CustomerProfileSerializer(
                    customer
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request):

        if request.user.role != "CUSTOMER":

            return Response(
                {
                    "success": False,
                    "message": (
                        "Only customers can update "
                        "this profile."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if not request.user.is_verified:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Please verify your phone number first."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        customer = (
            Customer.objects
            .filter(
                user=request.user
            )
            .first()
        )

        if customer is None:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Customer profile not found."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CustomerProfileSerializer(
            customer,
            data=request.data,
            partial=True,
        )

        if not serializer.is_valid():

            return Response(
                {
                    "success": False,
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer = serializer.save()

        return Response(
            {
                "success": True,
                "message": (
                    "Customer profile updated successfully."
                ),
                "profile": CustomerProfileSerializer(
                    customer
                ).data,
            },
            status=status.HTTP_200_OK,
        )

# ============================================================
# CUSTOMER APP - MY RO
# ============================================================

class MyROAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        # ----------------------------------------------------
        # CUSTOMER ONLY
        # ----------------------------------------------------

        if request.user.role != "CUSTOMER":

            return Response(
                {
                    "success": False,
                    "message": (
                        "Only customers can access "
                        "their RO."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ----------------------------------------------------
        # PHONE MUST BE VERIFIED
        # ----------------------------------------------------

        if not request.user.is_verified:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Please verify your phone "
                        "number first."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ----------------------------------------------------
        # CUSTOMER PROFILE
        # ----------------------------------------------------

        customer = (
            Customer.objects
            .filter(
                user=request.user
            )
            .first()
        )

        # ----------------------------------------------------
        # LEGACY CUSTOMER LINK
        # ----------------------------------------------------

        if customer is None:

            customer = (
                Customer.objects
                .filter(
                    phone=request.user.phone,
                    user__isnull=True,
                )
                .first()
            )

            if customer:

                customer.user = request.user

                customer.save(
                    update_fields=[
                        "user"
                    ]
                )

        # ----------------------------------------------------
        # PROFILE NOT FOUND
        # ----------------------------------------------------

        if customer is None:

            return Response(
                {
                    "success": False,
                    "profile_exists": False,
                    "message": (
                        "Customer profile is not "
                        "created yet."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ----------------------------------------------------
        # CUSTOMER'S ACTIVE RO ASSETS
        # ----------------------------------------------------

        assets = (
            ROAsset.objects
            .select_related(
                "ro_model",
                "current_customer",
            )
            .filter(
                current_customer=customer,
                is_active=True,
                status__in=[
                    "ASSIGNED",
                    "INSTALLED",
                    "SERVICE",
                    "REPAIR",
                ],
            )
            .order_by(
                "-id"
            )
        )

        serializer = MyROSerializer(
            assets,
            many=True,
        )

        return Response(
            {
                "success": True,
                "profile_exists": True,
                "count": assets.count(),
                "ros": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

class CustomerListAPIView(generics.ListAPIView):

    serializer_class = CustomerSerializer
    permission_classes = [IsVerifiedCustomerOrOperations]

    def get_queryset(self):

        user = self.request.user

        if user.role in ["ADMIN", "MANAGER", "OFFICE"]:
            return Customer.objects.all().order_by("-id")

        elif user.role == "ENGINEER":
            return Customer.objects.filter(
                assigned_engineer__user=user
            ).order_by("-id")

        elif user.role == "CUSTOMER":
            return Customer.objects.filter(
                phone=user.phone
            )

        return Customer.objects.none()

class MyCustomersAPIView(generics.ListAPIView):
    """Return customers assigned to the logged-in engineer."""

    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != "ENGINEER":
            return Customer.objects.none()

        return Customer.objects.filter(
            assigned_engineer__user=self.request.user
        ).select_related(
            "assigned_engineer__user"
        ).order_by("name", "id")

class CustomerCreateAPIView(generics.CreateAPIView):

    queryset = Customer.objects.all()

    serializer_class = CustomerSerializer

    permission_classes = [IsStaffOperator]

class CustomerDetailAPIView(generics.RetrieveAPIView):

    serializer_class = CustomerSerializer

    permission_classes = [IsVerifiedCustomerOrOperations]

    def get_queryset(self):
        return _customer_queryset_for(self.request.user)

class CustomerServiceHistoryAPIView(APIView):
    """
    Return service/job and physical parts history for one customer.

    Access rules:
        ADMIN / MANAGER / OFFICE
            -> Can view any customer

        ENGINEER
            -> Can view only assigned customers

        CUSTOMER
            -> Can view only own customer history

    URL:
        GET /api/customers/<customer_id>/service-history/
    """

    permission_classes = [IsAuthenticated]

    ALLOWED_STAFF_ROLES = [
        "ADMIN",
        "MANAGER",
        "OFFICE",
    ]

    def get(self, request, pk):

        user = request.user

        # ========================================================
        # FIND CUSTOMER
        # ========================================================

        try:

            customer = (
                Customer.objects
                .select_related(
                    "user",
                    "assigned_engineer__user",
                )
                .get(pk=pk)
            )

        except Customer.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "Customer not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ========================================================
        # ACCESS CONTROL
        # ========================================================

        # --------------------------------------------------------
        # CUSTOMER
        # --------------------------------------------------------

        if user.role == "CUSTOMER":

            # Phone verification required
            if not user.is_verified:

                return Response(
                    {
                        "success": False,
                        "message": (
                            "Please verify your phone number first."
                        ),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # ----------------------------------------------------
            # PRIMARY OWNERSHIP CHECK
            # ----------------------------------------------------

            if customer.user_id == user.id:

                pass

            # ----------------------------------------------------
            # LEGACY CUSTOMER SUPPORT
            # ----------------------------------------------------
            #
            # Old/imported customers may not have user linked.
            # In that case safely match by phone number.
            # ----------------------------------------------------

            elif (
                customer.user_id is None
                and customer.phone == user.phone
            ):

                customer.user = user

                customer.save(
                    update_fields=[
                        "user"
                    ]
                )

            # ----------------------------------------------------
            # NOT OWNER
            # ----------------------------------------------------

            else:

                return Response(
                    {
                        "success": False,
                        "message": (
                            "You can only access your own "
                            "service history."
                        ),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # --------------------------------------------------------
        # ENGINEER
        # --------------------------------------------------------

        elif user.role == "ENGINEER":

            if customer.assigned_engineer is None:

                return Response(
                    {
                        "success": False,
                        "message": (
                            "This customer is not assigned to you."
                        ),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if (
                customer.assigned_engineer.user_id
                != user.id
            ):

                return Response(
                    {
                        "success": False,
                        "message": (
                            "You can only access customers "
                            "assigned to you."
                        ),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # --------------------------------------------------------
        # ADMIN / MANAGER / OFFICE
        # --------------------------------------------------------

        elif user.role in self.ALLOWED_STAFF_ROLES:

            pass

        # --------------------------------------------------------
        # OTHER ROLES
        # --------------------------------------------------------

        else:

            return Response(
                {
                    "success": False,
                    "message": (
                        "You are not allowed to access "
                        "service history."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ========================================================
        # JOB HISTORY
        # ========================================================

        jobs = (
            Job.objects
            .filter(
                customer=customer
            )
            .select_related(
                "customer",
                "engineer__user",
                "ro_asset",
            )
            .prefetch_related(
                "parts_used__inventory_item__part",
                "parts_used__inventory_item__bag_item__engineer__user",
            )
            .order_by(
                "-created_at",
                "-id",
            )
        )

        # ========================================================
        # SERIALIZE JOBS
        # ========================================================

        job_data = JobSerializer(
            jobs,
            many=True,
            context={
                "request": request
            },
        ).data

        # ========================================================
        # TOTAL PARTS USED
        # ========================================================

        total_parts = 0

        for job in jobs:

            total_parts += sum(
                item.quantity or 0
                for item in job.parts_used.all()
            )

        # ========================================================
        # SUMMARY
        # ========================================================

        total_jobs = len(job_data)

        # ========================================================
        # RESPONSE
        # ========================================================

        return Response(
            {
                "success": True,

                # ------------------------------------------------
                # CUSTOMER
                # ------------------------------------------------

                "customer": {
                    "id": customer.id,
                    "customer_id": customer.customer_id,
                    "name": customer.name,
                    "phone": customer.phone,
                    "card_number": customer.card_number,
                    "old_card_number": customer.old_card_number,
                },

                # ------------------------------------------------
                # SUMMARY
                # ------------------------------------------------

                "summary": {
                    "total_jobs": total_jobs,
                    "total_parts_used": total_parts,
                },

                # ------------------------------------------------
                # TOP-LEVEL SUMMARY
                # ------------------------------------------------
                #
                # Backward compatibility.
                # Existing frontend/tests may directly access:
                #
                # response.data["total_jobs"]
                # response.data["total_parts_used"]
                #

                "total_jobs": total_jobs,

                "total_parts_used": total_parts,

                # ------------------------------------------------
                # PRIMARY HISTORY RESPONSE
                # ------------------------------------------------
                #
                # This is the clean/new API field.
                #

                "history": job_data,

                # ------------------------------------------------
                # BACKWARD COMPATIBILITY
                # ------------------------------------------------
                #
                # Older code/tests may use:
                #
                # response.data["jobs"]
                #

                "jobs": job_data,
            },
            status=status.HTTP_200_OK,
        )

class CustomerSearchAPIView(APIView):

    permission_classes = [IsVerifiedCustomerOrOperations]

    def get(self, request):

        q = request.GET.get("q", "").strip()

        queryset = _customer_queryset_for(request.user)

        if q:

            queryset = queryset.filter(

                Q(name__icontains=q) |
                Q(phone__icontains=q) |
                Q(card_number__icontains=q) |
                Q(customer_id__icontains=q)

            )

        serializer = CustomerSerializer(
            queryset.order_by("name"),
            many=True
        )

        return Response(serializer.data)

class CustomerUpdateAPIView(generics.UpdateAPIView):

    queryset = Customer.objects.all()

    serializer_class = CustomerSerializer

    permission_classes = [IsStaffOperator]

class WalkInCustomerAPIView(APIView):

    permission_classes = [IsEngineer]

    def post(self, request):

        serializer = WalkInCustomerSerializer(
            data=request.data
        )

        if serializer.is_valid():

            customer = serializer.save()

            ro_model = ROModel.objects.get(
                id=request.data["ro_model"]
            )

            asset = ROAsset.objects.get(
                id=request.data["asset_id"]
            )

            asset.current_customer = customer
            asset.status = "INSTALLED"
            asset.save()

            
            job = Job.objects.create(

                customer=customer,

                ro_asset=asset,

                engineer=request.user.employee_profile,

                job_type="INSTALLATION",

                priority="MEDIUM",

                scheduled_date=timezone.now(),

                status="IN_PROGRESS",

            )


            return Response(

                {

                    "success": True,

                    "customer_id": customer.id,

                    "job_id": job.id,

                    "asset_id": asset.id,

                },

                status=201,

            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

class AssignCustomerAPIView(APIView):

    permission_classes = [IsStaffOperator]

    def post(self, request, pk):

        # ---------------------------------------------------------
        # CUSTOMER
        # ---------------------------------------------------------
        try:
            customer = Customer.objects.get(pk=pk)

        except Customer.DoesNotExist:
            return Response(
                {"message": "Customer not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ---------------------------------------------------------
        # EMPLOYEE PROFILE ID
        # ---------------------------------------------------------
        employee_id = request.data.get("employee_id")

        if not employee_id:
            return Response(
                {"message": "Employee ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---------------------------------------------------------
        # ACTIVE EMPLOYEE
        # ENGINEER + OFFICE दोनों allowed
        # ---------------------------------------------------------
        try:
            employee = EmployeeProfile.objects.select_related(
                "user"
            ).get(
                id=employee_id,
                is_active=True,
                user__role__in=["ENGINEER", "OFFICE"],
            )

        except EmployeeProfile.DoesNotExist:
            return Response(
                {"message": "Employee not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ---------------------------------------------------------
        # SAVE CUSTOMER ASSIGNMENT
        # ---------------------------------------------------------
        customer.assigned_engineer = employee

        customer.save(
            update_fields=["assigned_engineer"]
        )

        # ---------------------------------------------------------
        # OFFICE STAFF
        #
        # Faizan जैसे Office Staff को Job.engineer में नहीं डालना।
        # Existing job को भी disturb नहीं करना।
        # ---------------------------------------------------------
        if employee.user.role == "OFFICE":

            return Response(
                {
                    "success": True,
                    "message": "Customer assigned to office staff successfully",
                    "customer_id": customer.id,
                    "employee_id": employee.id,
                    "employee_name": employee.user.get_full_name(),
                    "role": employee.user.role,
                },
                status=status.HTTP_200_OK,
            )

        # ---------------------------------------------------------
        # ENGINEER
        #
        # Existing engineer workflow यहाँ चलता रहेगा।
        # ---------------------------------------------------------
        job, created = Job.objects.get_or_create(

            customer=customer,

            defaults={
                "engineer": employee,

                "job_type": "INSTALLATION",

                "priority": "MEDIUM",

                "scheduled_date": timezone.now(),

                "status": "ASSIGNED",

                "customer_otp": str(
                    random.randint(100000, 999999)
                ),
            }
        )

        if not created:

            job.engineer = employee

            job.status = "ASSIGNED"

            job.customer_otp = str(
                random.randint(100000, 999999)
            )

            job.otp_verified = False

            job.save()

        return Response(
            {
                "success": True,
                "message": "Customer assigned successfully",
                "customer_id": customer.id,
                "employee_id": employee.id,
                "employee_name": employee.user.get_full_name(),
                "role": employee.user.role,
                "job_id": job.id,
                "otp": job.customer_otp,
            },
            status=status.HTTP_200_OK,
        )

# ============================================================
# CUSTOMER RENT & PAYMENT
# ============================================================



class CustomerRentAPIView(APIView):
    """
    Customer अपने current rent और payment history को देख सकता है.

    URL:
        GET /api/customers/rent/

    केवल CUSTOMER role के लिए.
    """

    permission_classes = [IsVerifiedCustomer]

    def get(self, request):

        # ----------------------------------------------------
        # CUSTOMER ROLE CHECK
        # ----------------------------------------------------

        if request.user.role != "CUSTOMER":
            return Response(
                {
                    "success": False,
                    "message": "Only customers can access rent details."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ----------------------------------------------------
        # CUSTOMER FIND
        # ----------------------------------------------------

        try:

            customer = Customer.objects.get(
                phone=request.user.phone
            )

        except Customer.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "Customer profile not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ----------------------------------------------------
        # CURRENT MONTH
        # ----------------------------------------------------

        today = timezone.now().date()

        current_month = today.replace(day=1)

        # ----------------------------------------------------
        # CURRENT RENT RECORD
        # ----------------------------------------------------

        rent_record, created = CustomerRentHistory.objects.get_or_create(

            customer=customer,

            rent_month=current_month,

            defaults={
                "expected_rent": customer.monthly_rent,
                "paid_amount": 0,
            },
        )

        # ----------------------------------------------------
        # IF RENT AMOUNT CHANGED
        # ----------------------------------------------------

        if rent_record.expected_rent != customer.monthly_rent:

            rent_record.expected_rent = customer.monthly_rent

            rent_record.save(
                update_fields=["expected_rent"]
            )

        # ----------------------------------------------------
        # PAYMENT CALCULATION
        # ----------------------------------------------------

        expected = float(
            rent_record.expected_rent or 0
        )

        paid = float(
            rent_record.paid_amount or 0
        )

        balance = max(
            expected - paid,
            0
        )

        # ----------------------------------------------------
        # PAYMENT STATUS
        # ----------------------------------------------------

        if expected <= 0:

            payment_status = "NO_RENT"

        elif paid >= expected:

            payment_status = "PAID"

        elif paid > 0:

            payment_status = "PARTIAL"

        else:

            payment_status = "PENDING"

        # ----------------------------------------------------
        # DUE DATE
        #
        # फिलहाल installation date के दिन को monthly
        # due date माना जा रहा है.
        #
        # Example:
        # Installation = 15 August
        # September due date = 15 September
        # ----------------------------------------------------

        if customer.installation_date:

            installation_day = customer.installation_date.day

        else:

            installation_day = 1

        last_day = calendar.monthrange(
            today.year,
            today.month
        )[1]

        due_day = min(
            installation_day,
            last_day
        )

        due_date = date(
            today.year,
            today.month,
            due_day
        )

        # ----------------------------------------------------
        # HISTORY
        # ----------------------------------------------------

        history = CustomerRentHistory.objects.filter(
            customer=customer
        ).order_by(
            "-rent_month",
            "-id"
        )

        history_data = []

        for item in history:

            item_expected = float(
                item.expected_rent or 0
            )

            item_paid = float(
                item.paid_amount or 0
            )

            item_balance = max(
                item_expected - item_paid,
                0
            )

            if item_expected <= 0:

                item_status = "NO_RENT"

            elif item_paid >= item_expected:

                item_status = "PAID"

            elif item_paid > 0:

                item_status = "PARTIAL"

            else:

                item_status = "PENDING"

            history_data.append(
                {
                    "id": item.id,

                    "rent_month": (
                        item.rent_month.isoformat()
                        if item.rent_month
                        else None
                    ),

                    "expected_rent": item_expected,

                    "paid_amount": item_paid,

                    "balance": item_balance,

                    "status": item_status,

                    "raw_value": item.raw_value,

                    "remarks": item.remarks,

                    "created_at": (
                        item.created_at.isoformat()
                        if item.created_at
                        else None
                    ),
                }
            )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return Response(
            {
                "success": True,

                "customer": {
                    "id": customer.id,
                    "customer_id": customer.customer_id,
                    "name": customer.name,
                    "phone": customer.phone,
                    "card_number": customer.card_number,
                },

                "ro": {
                    "model": customer.ro_model,
                    "installation_date": (
                        customer.installation_date.isoformat()
                        if customer.installation_date
                        else None
                    ),
                    "installation_charge": float(
                        customer.installation_charge or 0
                    ),
                    "monthly_rent": float(
                        customer.monthly_rent or 0
                    ),
                    "security_deposit": float(
                        customer.security_deposit or 0
                    ),
                    "is_active": customer.is_active,
                },

                "current_rent": {
                    "id": rent_record.id,

                    "rent_month": current_month.isoformat(),

                    "expected_rent": expected,

                    "paid_amount": paid,

                    "balance": balance,

                    "due_date": due_date.isoformat(),

                    "status": payment_status,
                },

                "history": history_data,
            },

            status=status.HTTP_200_OK,
        )

# ============================================================
# ADMIN / MANAGER / OFFICE RENT MANAGEMENT
# ============================================================

class RentManagementAPIView(APIView):
    """
    Admin, Manager aur Office ke liye
    sabhi customers ka current rent aur rent history.

    GET:
        /api/customers/rent-management/
    """

    permission_classes = [IsAuthenticated]

    ALLOWED_ROLES = [
        "ADMIN",
        "MANAGER",
        "OFFICE",
    ]

    def get(self, request):

        # ----------------------------------------------------
        # ROLE CHECK
        # ----------------------------------------------------

        if request.user.role not in self.ALLOWED_ROLES:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Only Admin, Manager or Office "
                        "can access rent management."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ----------------------------------------------------
        # CUSTOMERS
        # ----------------------------------------------------

        customers = Customer.objects.filter(
            is_active=True
        ).order_by(
            "name",
            "id",
        )

        result = []

        # ----------------------------------------------------
        # CURRENT DATE
        # ----------------------------------------------------

        today = timezone.now().date()

        current_month = today.replace(
            day=1
        )

        # ----------------------------------------------------
        # LOOP CUSTOMERS
        # ----------------------------------------------------

        for customer in customers:

            # ------------------------------------------------
            # CURRENT MONTH RENT
            # ------------------------------------------------

            rent_record, created = (
                CustomerRentHistory.objects.get_or_create(

                    customer=customer,

                    rent_month=current_month,

                    defaults={
                        "expected_rent":
                            customer.monthly_rent,

                        "paid_amount": 0,
                    },
                )
            )

            # -----------------------------------------------
            # UPDATE RENT IF CUSTOMER RENT CHANGED
            # -----------------------------------------------

            if (
                rent_record.expected_rent
                != customer.monthly_rent
            ):

                rent_record.expected_rent = (
                    customer.monthly_rent
                )

                rent_record.save(
                    update_fields=[
                        "expected_rent"
                    ]
                )

            # ------------------------------------------------
            # AMOUNTS
            # ------------------------------------------------

            expected = float(
                rent_record.expected_rent or 0
            )

            paid = float(
                rent_record.paid_amount or 0
            )

            balance = max(
                expected - paid,
                0,
            )

            # ------------------------------------------------
            # STATUS
            # ------------------------------------------------

            if expected <= 0:

                payment_status = "NO_RENT"

            elif paid >= expected:

                payment_status = "PAID"

            elif paid > 0:

                payment_status = "PARTIAL"

            else:

                payment_status = "PENDING"

            # ------------------------------------------------
            # DUE DATE
            # ------------------------------------------------

            if customer.installation_date:

                installation_day = (
                    customer.installation_date.day
                )

            else:

                installation_day = 1

            last_day = calendar.monthrange(
                today.year,
                today.month,
            )[1]

            due_day = min(
                installation_day,
                last_day,
            )

            due_date = date(
                today.year,
                today.month,
                due_day,
            )

            # ------------------------------------------------
            # RENT HISTORY
            # ------------------------------------------------

            history = (
                CustomerRentHistory.objects
                .filter(
                    customer=customer
                )
                .order_by(
                    "-rent_month",
                    "-id",
                )
            )

            history_data = []

            for item in history:

                item_expected = float(
                    item.expected_rent or 0
                )

                item_paid = float(
                    item.paid_amount or 0
                )

                item_balance = max(
                    item_expected - item_paid,
                    0,
                )

                if item_expected <= 0:

                    item_status = "NO_RENT"

                elif item_paid >= item_expected:

                    item_status = "PAID"

                elif item_paid > 0:

                    item_status = "PARTIAL"

                else:

                    item_status = "PENDING"

                history_data.append(
                    {
                        "id": item.id,

                        "rent_month": (
                            item.rent_month.isoformat()
                            if item.rent_month
                            else None
                        ),

                        "expected_rent":
                            item_expected,

                        "paid_amount":
                            item_paid,

                        "balance":
                            item_balance,

                        "status":
                            item_status,

                        "raw_value":
                            item.raw_value,

                        "remarks":
                            item.remarks,

                        "created_at": (
                            item.created_at.isoformat()
                            if item.created_at
                            else None
                        ),
                    }
                )

            # ------------------------------------------------
            # CUSTOMER RESULT
            # ------------------------------------------------

            result.append(
                {
                    "customer": {
                        "id":
                            customer.id,

                        "customer_id":
                            customer.customer_id,

                        "name":
                            customer.name,

                        "phone":
                            customer.phone,

                        "card_number":
                            customer.card_number,

                        "old_card_number":
                            customer.old_card_number,
                    },

                    "current_rent": {
                        "rent_month":
                            current_month.isoformat(),

                        "expected_rent":
                            expected,

                        "paid_amount":
                            paid,

                        "balance":
                            balance,

                        "status":
                            payment_status,

                        "due_date":
                            due_date.isoformat(),
                    },

                    "ro": {
                        "model":
                            customer.ro_model,

                        "monthly_rent":
                            float(
                                customer.monthly_rent or 0
                            ),

                        "installation_charge":
                            float(
                                customer.installation_charge
                                or 0
                            ),

                        "security_deposit":
                            float(
                                customer.security_deposit
                                or 0
                            ),

                        "installation_date": (
                            customer.installation_date.isoformat()
                            if customer.installation_date
                            else None
                        ),
                    },

                    "history":
                        history_data,
                }
            )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return Response(
            {
                "success": True,

                "count":
                    len(result),

                "customers":
                    result,
            },
            status=status.HTTP_200_OK,
        )

# ============================================================
# OFFICE RENT PAYMENT
# ============================================================

class RentPaymentCreateAPIView(APIView):
    """
    Office / Admin / Manager customer ka rent payment record
    create kar sakte hain.

    Referral wallet rules:

    1. Rent customer ka monthly rent ₹100 se kam nahi hona chahiye.
    2. Eligible referral wallet se maximum ₹50 per rent month use hoga.
    3. Customer ko minimum ₹100 actual payment karna hoga.
    4. Same rent month mein referral wallet dobara use nahi hoga.
    5. Next month phir ₹50 available hoga.
    6. Welcome reward RENT payment ke liye eligible nahi hai.

    POST:
        /api/customers/rent-management/payment/
    """

    permission_classes = [IsAuthenticated]

    ALLOWED_ROLES = [
        "ADMIN",
        "MANAGER",
        "OFFICE",
    ]

    @transaction.atomic
    def post(self, request):

        # ====================================================
        # ROLE CHECK
        # ====================================================

        if request.user.role not in self.ALLOWED_ROLES:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Only Admin, Manager or Office "
                        "can record rent payment."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ====================================================
        # INPUT
        # ====================================================

        customer_id = request.data.get(
            "customer_id"
        )

        amount = request.data.get(
            "amount"
        )

        payment_mode = request.data.get(
            "payment_mode",
            "CASH",
        )

        payment_date = request.data.get(
            "payment_date"
        )

        remarks = request.data.get(
            "remarks",
            "",
        )

        # ====================================================
        # REQUIRED FIELDS
        # ====================================================

        if not customer_id:

            return Response(
                {
                    "success": False,
                    "message":
                        "customer_id is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if amount in [
            None,
            "",
        ]:

            return Response(
                {
                    "success": False,
                    "message":
                        "amount is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ====================================================
        # CUSTOMER
        # ====================================================

        try:

            customer = (
                Customer.objects
                .select_related("user")
                .get(
                    id=customer_id
                )
            )

        except Customer.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message":
                        "Customer not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ====================================================
        # MONTHLY RENT VALIDATION
        # ====================================================

        customer_monthly_rent = Decimal(
            str(
                customer.monthly_rent or 0
            )
        ).quantize(
            Decimal("0.01")
        )

        if customer_monthly_rent < Decimal("100.00"):

            return Response(
                {
                    "success": False,
                    "message": (
                        "Monthly rent cannot be less "
                        "than ₹100."
                    ),
                    "monthly_rent":
                        float(customer_monthly_rent),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ====================================================
        # AMOUNT
        #
        # `amount` means the total rent amount customer
        # wants to settle in this transaction.
        #
        # Example:
        #
        # Monthly rent = ₹300
        # Wallet       = ₹50
        # Cash/UPI     = ₹250
        #
        # Request amount = ₹300
        # ====================================================

        try:

            requested_amount = Decimal(
                str(amount)
            ).quantize(
                Decimal("0.01")
            )

        except Exception:

            return Response(
                {
                    "success": False,
                    "message":
                        "Invalid payment amount.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if requested_amount <= 0:

            return Response(
                {
                    "success": False,
                    "message":
                        "Payment amount must be greater than zero.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ====================================================
        # PAYMENT MODE
        # ====================================================

        allowed_modes = [
            "CASH",
            "UPI",
            "BANK",
            "OTHER",
        ]

        payment_mode = str(
            payment_mode
        ).upper().strip()

        if payment_mode not in allowed_modes:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Invalid payment mode. "
                        "Use CASH, UPI, BANK or OTHER."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ====================================================
        # PAYMENT DATE
        # ====================================================

        if payment_date:

            try:

                payment_date_obj = date.fromisoformat(
                    str(payment_date)
                )

            except ValueError:

                return Response(
                    {
                        "success": False,
                        "message":
                            "Invalid payment_date. "
                            "Use YYYY-MM-DD.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        else:

            payment_date_obj = (
                timezone.now().date()
            )

        # ====================================================
        # CURRENT RENT MONTH
        # ====================================================

        rent_month = payment_date_obj.replace(
            day=1
        )

        # ====================================================
        # WALLET REFERENCE
        #
        # Example:
        #
        # 2026-08
        # 2026-09
        #
        # This is what makes the ₹50 benefit monthly.
        # ====================================================

        wallet_reference_type = (
            "RENT_PAYMENT"
        )

        wallet_reference_id = (
            rent_month.isoformat()
        )

        # ====================================================
        # RENT HISTORY
        # ====================================================

        rent_record, created = (
            CustomerRentHistory.objects
            .select_for_update()
            .get_or_create(

                customer=customer,

                rent_month=rent_month,

                defaults={
                    "expected_rent":
                        customer_monthly_rent,

                    "paid_amount":
                        Decimal("0.00"),
                },
            )
        )

        # ====================================================
        # UPDATE EXPECTED RENT
        # ====================================================

        if (
            rent_record.expected_rent
            != customer_monthly_rent
        ):

            rent_record.expected_rent = (
                customer_monthly_rent
            )

            rent_record.save(
                update_fields=[
                    "expected_rent",
                   
                ]
            )

        # ====================================================
        # CURRENT BALANCE
        # ====================================================

        current_expected = Decimal(
            str(
                rent_record.expected_amount
                if hasattr(
                    rent_record,
                    "expected_amount"
                )
                else rent_record.expected_rent
                or 0
            )
        ).quantize(
            Decimal("0.01")
        )

        current_paid = Decimal(
            str(
                rent_record.paid_amount
                or 0
            )
        ).quantize(
            Decimal("0.01")
        )

        current_balance = max(
            current_expected
            - current_paid,
            Decimal("0.00"),
        )

        # ====================================================
        # NOTHING OUTSTANDING
        # ====================================================

        if current_balance <= 0:

            return Response(
                {
                    "success": False,
                    "message":
                        "There is no outstanding rent balance.",
                    "expected_rent":
                        float(current_expected),
                    "already_paid":
                        float(current_paid),
                    "balance":
                        0.0,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ====================================================
        # REQUESTED TOTAL CANNOT EXCEED OUTSTANDING
        # ====================================================

        if requested_amount > current_balance:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Payment amount cannot be greater "
                        "than the current outstanding balance."
                    ),

                    "expected_rent":
                        float(current_expected),

                    "already_paid":
                        float(current_paid),

                    "balance":
                        float(current_balance),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ====================================================
        # IMPORTANT
        #
        # Wallet is calculated against the amount being
        # settled, but customer must still pay minimum ₹100.
        #
        # Example:
        #
        # requested_amount = ₹300
        # wallet = ₹50
        # actual payment = ₹250
        #
        # requested_amount = ₹120
        # wallet = ₹20
        # actual payment = ₹100
        #
        # requested_amount = ₹100
        # wallet = ₹0
        # actual payment = ₹100
        # ====================================================

        wallet_used = Decimal("0.00")

        # ====================================================
        # ONLY CUSTOMER-OWNED WALLET CAN BE USED
        # ====================================================

        wallet_user = getattr(
            customer,
            "user",
            None,
        )

        if wallet_user is not None:

            try:

                wallet_used = (
                    calculate_max_redeemable(
                        user=wallet_user,

                        bill_amount=requested_amount,

                        category="RENT",

                        reference_type=(
                            wallet_reference_type
                        ),

                        reference_id=(
                            wallet_reference_id
                        ),
                    )
                )

            except Exception:

                wallet_used = Decimal("0.00")

        wallet_used = Decimal(
            str(
                wallet_used or 0
            )
        ).quantize(
            Decimal("0.01")
        )

        # ====================================================
        # ACTUAL CASH / UPI / BANK PAYMENT
        # ====================================================

        actual_payment_amount = (
            requested_amount
            - wallet_used
        )

        if actual_payment_amount < Decimal(
            "0.00"
        ):

            actual_payment_amount = (
                Decimal("0.00")
            )

        # ====================================================
        # MINIMUM ₹100 CUSTOMER PAYMENT
        #
        # Wallet can never reduce customer's payable
        # rent below ₹100.
        # ====================================================

        if (
            actual_payment_amount
            < Decimal("100.00")
        ):

            # Recalculate wallet according to the
            # minimum payable requirement.

            allowed_wallet = max(
                requested_amount
                - Decimal("100.00"),
                Decimal("0.00"),
            )

            wallet_used = min(
                wallet_used,
                allowed_wallet,
            )

            actual_payment_amount = (
                requested_amount
                - wallet_used
            )

        # ====================================================
        # WALLET REDEMPTION
        #
        # Do this only if wallet actually has something
        # to contribute.
        # ====================================================

        wallet_result = None

        if (
            wallet_used > 0
            and wallet_user is not None
        ):

            wallet_result = redeem_wallet(

                user=wallet_user,

                bill_amount=requested_amount,

                category="RENT",

                reference_type=(
                    wallet_reference_type
                ),

                reference_id=(
                    wallet_reference_id
                ),
            )

            # ------------------------------------------------
            # Never trust the earlier quote blindly.
            # Use actual atomic redemption result.
            # ------------------------------------------------

            wallet_used = Decimal(
                str(
                    wallet_result.get(
                        "wallet_used",
                        Decimal("0.00"),
                    )
                )
            ).quantize(
                Decimal("0.01")
            )

            actual_payment_amount = (
                requested_amount
                - wallet_used
            )

        # ====================================================
        # SAFETY CHECK
        # ====================================================

        if actual_payment_amount < Decimal(
            "100.00"
        ):

            # This should normally never happen because
            # redeem_wallet itself enforces the ₹100 rule.

            raise ValidationError(
                "Customer payable rent cannot be less than ₹100."
            )

        # ====================================================
        # UPDATE PAID AMOUNT
        #
        # IMPORTANT:
        # Only actual cash/online payment is added to the
        # rent payment history.
        #
        # Wallet is separately recorded in wallet ledger.
        # ====================================================

        rent_record.paid_amount = (
            current_paid
            + actual_payment_amount
        )

        rent_record.save(
            update_fields=[
                "paid_amount",
                
            ]
        )

        # ====================================================
        # COLLECTED BY
        # ====================================================

        collector = None

        try:

            collector = (
                EmployeeProfile.objects.get(
                    user=request.user
                )
            )

        except EmployeeProfile.DoesNotExist:

            collector = None

        # ====================================================
        # CREATE CASH / ONLINE PAYMENT TRANSACTION
        # ====================================================

        payment = (
            CustomerRentPayment.objects.create(

                customer=customer,

                rent_history=rent_record,

                amount=actual_payment_amount,

                payment_date=payment_date_obj,

                payment_mode=payment_mode,

                remarks=str(
                    remarks
                ),

                collected_by=collector,
            )
        )

        # ====================================================
        # NEW BALANCE
        # ====================================================

        new_paid = Decimal(
            str(
                rent_record.paid_amount
                or 0
            )
        ).quantize(
            Decimal("0.01")
        )

        new_balance = max(
            current_expected
            - new_paid,
            Decimal("0.00"),
        )

        # ====================================================
        # PAYMENT STATUS
        # ====================================================

        if current_expected <= 0:

            payment_status = "NO_RENT"

        elif new_paid >= current_expected:

            payment_status = "PAID"

        elif new_paid > 0:

            payment_status = "PARTIAL"

        else:

            payment_status = "PENDING"

        # ====================================================
        # FINAL RESPONSE
        # ====================================================

        return Response(
            {
                "success": True,

                "message":
                    "Rent payment recorded successfully.",

                "payment": {
                    "id":
                        payment.id,

                    # Actual CASH / UPI / BANK amount
                    "amount":
                        float(
                            payment.amount
                        ),

                    "payment_date":
                        payment.payment_date.isoformat(),

                    "payment_mode":
                        payment.payment_mode,

                    "remarks":
                        payment.remarks,

                    "collected_by":
                        (
                            request.user.get_full_name()
                            or request.user.phone
                        ),
                },

                # ------------------------------------------------
                # WALLET DETAILS
                # ------------------------------------------------

                "wallet": {
                    "used":
                        float(
                            wallet_used
                        ),

                    "reference_type":
                        wallet_reference_type,

                    "reference_id":
                        wallet_reference_id,

                    "enabled":
                        wallet_used > 0,
                },

                # ------------------------------------------------
                # CUSTOMER ACTUAL PAYABLE
                # ------------------------------------------------

                "customer_payment": {
                    "requested_rent":
                        float(
                            requested_amount
                        ),

                    "wallet_used":
                        float(
                            wallet_used
                        ),

                    "cash_or_online_paid":
                        float(
                            actual_payment_amount
                        ),
                },

                "customer": {
                    "id":
                        customer.id,

                    "customer_id":
                        customer.customer_id,

                    "name":
                        customer.name,

                    "phone":
                        customer.phone,
                },

                "rent": {
                    "rent_month":
                        rent_month.isoformat(),

                    "expected_rent":
                        float(
                            current_expected
                        ),

                    "paid_amount":
                        float(
                            new_paid
                        ),

                    "balance":
                        float(
                            new_balance
                        ),

                    "status":
                        payment_status,
                },
            },
            status=status.HTTP_201_CREATED,
        )

# ============================================================
# RENT PAYMENT HISTORY
# ============================================================

class RentPaymentHistoryAPIView(APIView):
    """
    Admin / Manager / Office rent payment history dekh sakte hain.

    Optional:
        customer_id

    Examples:

        GET /api/customers/rent-management/payments/

        GET /api/customers/rent-management/payments/?customer_id=123
    """

    permission_classes = [IsAuthenticated]

    ALLOWED_ROLES = [
        "ADMIN",
        "MANAGER",
        "OFFICE",
    ]

    def get(self, request):

        # ----------------------------------------------------
        # ROLE CHECK
        # ----------------------------------------------------

        if request.user.role not in self.ALLOWED_ROLES:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Only Admin, Manager or Office "
                        "can view rent payment history."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ----------------------------------------------------
        # OPTIONAL CUSTOMER FILTER
        # ----------------------------------------------------

        customer_id = request.query_params.get(
            "customer_id"
        )

        payments = (
            CustomerRentPayment.objects
            .select_related(
                "customer",
                "rent_history",
                "collected_by__user",
            )
            .order_by(
                "-payment_date",
                "-id",
            )
        )

        # ----------------------------------------------------
        # FILTER CUSTOMER
        # ----------------------------------------------------

        if customer_id:

            try:

                customer_id = int(
                    customer_id
                )

            except ValueError:

                return Response(
                    {
                        "success": False,
                        "message":
                            "Invalid customer_id.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payments = payments.filter(
                customer_id=customer_id
            )

        # ----------------------------------------------------
        # RESPONSE DATA
        # ----------------------------------------------------

        payment_data = []

        for payment in payments:

            customer = payment.customer

            collector_name = ""

            if payment.collected_by:

                collector_user = (
                    payment.collected_by.user
                )

                full_name = (
                    collector_user.get_full_name()
                    or ""
                ).strip()

                if full_name:
                    collector_name = full_name

                elif getattr(
                    collector_user,
                    "role",
                    None,
                ):
                    collector_name = str(
                        collector_user.role
                    )

                else:
                    collector_name = (
                        collector_user.phone
                    )
            payment_data.append(
                {
                    "id":
                        payment.id,

                    "customer": {
                        "id":
                            customer.id,

                        "customer_id":
                            customer.customer_id,

                        "name":
                            customer.name,

                        "phone":
                            customer.phone,

                        "card_number":
                            customer.card_number,

                        "old_card_number":
                            customer.old_card_number,
                    },

                    "rent_month": (
                        payment.rent_history
                        .rent_month
                        .isoformat()
                        if payment.rent_history
                        and payment.rent_history.rent_month
                        else None
                    ),

                    "amount":
                        float(
                            payment.amount or 0
                        ),

                    "payment_date":
                        (
                            payment.payment_date
                            .isoformat()
                            if payment.payment_date
                            else None
                        ),

                    "payment_mode":
                        payment.payment_mode,

                    "remarks":
                        payment.remarks,

                    "collected_by":
                        collector_name,

                    "created_at": (
                        payment.created_at
                        .isoformat()
                        if payment.created_at
                        else None
                    ),
                }
            )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return Response(
            {
                "success": True,

                "count":
                    len(payment_data),

                "payments":
                    payment_data,
            },
            status=status.HTTP_200_OK,
        )

# ============================================================
# CUSTOMER APP PROFILE
# ============================================================
