from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import ScopedRateThrottle
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import AuthSecurityEvent, User
from customers.models import Customer

from .serializers import (
    UserSerializer,
    CustomerRegisterSerializer,
)

from .services.otp import (
    create_phone_otp,
    verify_phone_otp,
)
from .services.sms import SMSDeliveryError, send_customer_verification_otp


class ProductionScopedRateThrottle(ScopedRateThrottle):
    def get_cache_key(self, request, view):
        if settings.DEBUG or settings.DISABLE_AUTH_THROTTLING:
            return None
        return super().get_cache_key(request, view)


def _security_event(request, event_type, user=None, **details):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    ip_address = forwarded or request.META.get("REMOTE_ADDR") or None
    AuthSecurityEvent.objects.create(
        user=user,
        event_type=event_type,
        ip_address=ip_address,
        device_id=request.headers.get("X-ARI-Device-ID", "")[:64],
        details=details,
    )


# ============================================================
# CUSTOMER REGISTRATION
# ============================================================

class CustomerRegisterAPIView(APIView):

    permission_classes = []
    throttle_classes = [ProductionScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request):

        serializer = CustomerRegisterSerializer(
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

        user = serializer.save()

        return Response(
            {
                "success": True,
                "message": (
                    "Customer registered successfully. "
                    "Verify the phone OTP and set the final password to activate the account."
                ),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# SEND OTP
# ============================================================

class SendOTPAPIView(APIView):

    permission_classes = []
    throttle_classes = [ProductionScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request):

        phone = request.data.get(
            "phone"
        )

        if not phone:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Phone number is required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:

            user = User.objects.get(
                phone=phone,
                role="CUSTOMER",
            )

        except User.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Customer not found."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:

            phone_otp = create_phone_otp(user)

        except ValueError as exc:

            return Response(
                {
                    "success": False,
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            send_customer_verification_otp(user.phone, phone_otp.otp)
        except SMSDeliveryError:
            phone_otp.is_used = True
            phone_otp.save(update_fields=["is_used"])
            return Response(
                {
                    "success": False,
                    "message": "OTP delivery is temporarily unavailable. Please try again.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # ----------------------------------------------------
        # IMPORTANT
        # ----------------------------------------------------
        # Actual OTP is NOT returned by the API.
        #
        # Delivery is handled by the configured production SMS backend.
        # ----------------------------------------------------

        return Response(
            {
                "success": True,
                "message": (
                    "OTP sent successfully."
                ),
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# VERIFY OTP
# ============================================================

class VerifyOTPAPIView(APIView):

    permission_classes = []
    throttle_classes = [ProductionScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request):

        phone = request.data.get(
            "phone"
        )

        otp = request.data.get(
            "otp"
        )
        # Accept the explicit onboarding field and retain compatibility with
        # older app builds that submitted the generic `password` key.
        new_password = request.data.get("new_password") or request.data.get(
            "password"
        )

        if not phone or not otp or not new_password:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Phone number, OTP and final password are required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            not str(otp).isdigit()
            or len(str(otp)) != 6
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "OTP must be a 6-digit number."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:

            user = User.objects.get(
                phone=phone,
                role="CUSTOMER",
            )

        except User.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Customer not found."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if new_password:
            try:
                validate_password(new_password, user=user)
            except DjangoValidationError as exc:
                return Response(
                    {"success": False, "message": " ".join(exc.messages)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:

            validate_password(
                new_password,
                user=user,
            )

        except DjangoValidationError as exc:

            return Response(
                {
                    "success": False,
                    "message": " ".join(exc.messages),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:

            user = verify_phone_otp(
                user,
                otp,
                new_password,
            )

        except ValueError as exc:

            return Response(
                {
                    "success": False,
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password:
            user.set_password(new_password)
            user.save(update_fields=["password"])

        # Existing/imported customers activate their own record by proving
        # ownership of the exact registered phone number.
        customer = Customer.objects.filter(phone=user.phone).first()
        if customer is not None:
            if customer.user_id not in (None, user.id):
                return Response(
                    {"success": False, "message": "This customer record is already linked to another account."},
                    status=status.HTTP_409_CONFLICT,
                )
            if customer.user_id is None:
                customer.user = user
                customer.save(update_fields=["user"])

        refresh = RefreshToken.for_user(user)
        _security_event(request, "OTP_VERIFIED", user=user, existing_customer=customer is not None)

        return Response(
            {
                "success": True,
                "message": (
                    "Phone number verified successfully."
                ),
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "existing_customer_linked": customer is not None,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# LOGIN
# ============================================================

class LoginAPIView(APIView):

    permission_classes = []
    throttle_classes = [ProductionScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):

        phone = request.data.get(
            "phone"
        )

        password = request.data.get(
            "password"
        )

        if not phone or not password:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Phone and password are required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        candidate = User.objects.filter(phone=phone).first()
        if candidate and candidate.role == "CUSTOMER" and (
            not candidate.is_verified or not candidate.is_active
        ):
            return Response(
                {
                    "success": False,
                    "message": "Verify your phone number before signing in.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if candidate is not None and candidate.locked_until is not None:
            if candidate.locked_until > timezone.now():
                _security_event(request, "LOGIN_FAILED", user=candidate, reason="ACCOUNT_LOCKED")
                return Response(
                    {"success": False, "message": "Account is temporarily locked. Please try again later."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            candidate.failed_login_attempts = 0
            candidate.locked_until = None
            candidate.save(update_fields=["failed_login_attempts", "locked_until"])

        user = authenticate(
            phone=phone,
            password=password,
        )

        if user is None:
            if candidate is not None:
                candidate.failed_login_attempts += 1
                event_type = "LOGIN_FAILED"
                if candidate.failed_login_attempts >= 5:
                    candidate.locked_until = timezone.now() + timedelta(minutes=15)
                    event_type = "ACCOUNT_LOCKED"
                candidate.save(update_fields=["failed_login_attempts", "locked_until"])
                _security_event(request, event_type, user=candidate)

            return Response(
                {
                    "success": False,
                    "message": (
                        "Invalid phone or password"
                    ),
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if user.role == "CUSTOMER" and not user.is_verified:
            _security_event(request, "LOGIN_FAILED", user=user, reason="PHONE_NOT_VERIFIED")
            return Response(
                {"success": False, "message": "Please verify your mobile number before login."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user.failed_login_attempts or user.locked_until is not None:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.save(update_fields=["failed_login_attempts", "locked_until"])

        _security_event(request, "LOGIN_SUCCESS", user=user)

        refresh = RefreshToken.for_user(
            user
        )

        return Response(
            {
                "success": True,
                "access": str(
                    refresh.access_token
                ),
                "refresh": str(
                    refresh
                ),
                "user": UserSerializer(
                    user
                ).data,
            }
        )


# ============================================================
# CHANGE PASSWORD
# ============================================================

class ChangePasswordAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def post(self, request):

        old_password = request.data.get(
            "old_password"
        )

        new_password = request.data.get(
            "new_password"
        )

        if not old_password or not new_password:

            return Response(
                {
                    "success": False,
                    "message": (
                        "All fields are required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user

        if not check_password(
            old_password,
            user.password,
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "Old password is incorrect."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(
            new_password
        )

        user.save()

        refresh = RefreshToken.for_user(
            user
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Password changed successfully."
                ),
                "access": str(
                    refresh.access_token
                ),
                "refresh": str(
                    refresh
                ),
            }
        )
