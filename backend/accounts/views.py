from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import ScopedRateThrottle

from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.hashers import check_password

from .models import User

from .serializers import (
    UserSerializer,
    CustomerRegisterSerializer,
)

from .services.otp import (
    create_phone_otp,
    verify_phone_otp,
)


# ============================================================
# CUSTOMER REGISTRATION
# ============================================================

class CustomerRegisterAPIView(APIView):

    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
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
                    "Phone verification is pending."
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
    throttle_classes = [ScopedRateThrottle]
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

            create_phone_otp(user)

        except ValueError as exc:

            return Response(
                {
                    "success": False,
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # IMPORTANT
        # ----------------------------------------------------
        # Actual OTP is NOT returned by the API.
        #
        # Production mein yahin SMS provider call hoga.
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
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request):

        phone = request.data.get(
            "phone"
        )

        otp = request.data.get(
            "otp"
        )

        if not phone or not otp:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Phone number and OTP "
                        "are required."
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

        try:

            user = verify_phone_otp(
                user,
                otp,
            )

        except ValueError as exc:

            return Response(
                {
                    "success": False,
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "success": True,
                "message": (
                    "Phone number verified successfully."
                ),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# LOGIN
# ============================================================

class LoginAPIView(APIView):

    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
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

        user = authenticate(
            phone=phone,
            password=password,
        )

        if user is None:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Invalid phone or password"
                    ),
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

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