import hashlib
import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.crypto import constant_time_compare
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import UserSerializer
from .services.sms import SMSDeliveryError, send_admin_login_otp
from .views import LoginAPIView, ProductionScopedRateThrottle


ADMIN_MFA_SALT = "ari-admin-login-mfa-v1"
ADMIN_MFA_MAX_AGE_SECONDS = 300


def _mask_phone(phone):
    value = str(phone or "")
    if len(value) < 4:
        return "••••"
    return f"••••••{value[-4:]}"


def _mfa_replay_cache_key(payload):
    nonce = str(payload.get("nonce") or "")
    user_id = str(payload.get("user_id") or "")
    digest = hashlib.sha256(f"{user_id}:{nonce}".encode("utf-8")).hexdigest()
    return f"ari:admin-mfa:used:{digest}"


class SecureLoginAPIView(LoginAPIView):
    """Normal login for users, plus mandatory second factor for Admin."""

    def post(self, request):
        response = super().post(request)
        if response.status_code != status.HTTP_200_OK:
            return response

        data = dict(response.data or {})
        user_data = data.get("user") or {}
        if str(user_data.get("role") or "").upper() != "ADMIN":
            return response

        # The password was valid, but Admin must not receive a usable session
        # until the registered mobile OTP is verified. Blacklist the temporary
        # refresh token created by the base login flow before returning.
        raw_refresh = data.get("refresh")
        if raw_refresh:
            try:
                RefreshToken(str(raw_refresh)).blacklist()
            except Exception:
                pass

        user = User.objects.filter(
            pk=user_data.get("id"),
            role="ADMIN",
            is_active=True,
        ).first()
        if user is None:
            return Response(
                {"success": False, "message": "Admin account is unavailable."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        otp = f"{secrets.randbelow(1000000):06d}"
        try:
            send_admin_login_otp(user.phone, otp)
        except SMSDeliveryError:
            return Response(
                {
                    "success": False,
                    "message": "Admin verification code could not be delivered. Please try again.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        device_id = str(request.headers.get("X-ARI-Device-ID", "") or "").strip()[:64]
        challenge = signing.dumps(
            {
                "user_id": user.pk,
                "otp_hash": make_password(otp),
                "device_id": device_id,
                "password_state": user.get_session_auth_hash(),
                "nonce": secrets.token_urlsafe(18),
            },
            salt=ADMIN_MFA_SALT,
            compress=True,
        )
        return Response(
            {
                "success": True,
                "mfa_required": True,
                "challenge": challenge,
                "expires_in_seconds": ADMIN_MFA_MAX_AGE_SECONDS,
                "destination": _mask_phone(user.phone),
                "message": "Admin verification code sent to the registered mobile number.",
            },
            status=status.HTTP_202_ACCEPTED,
        )


class AdminMFAVerifyAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ProductionScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request):
        challenge = str(request.data.get("challenge") or "")
        otp = str(request.data.get("otp") or "").strip()
        if not challenge or len(otp) != 6 or not otp.isdigit():
            return Response(
                {"success": False, "message": "Enter the 6-digit admin verification code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = signing.loads(
                challenge,
                salt=ADMIN_MFA_SALT,
                max_age=ADMIN_MFA_MAX_AGE_SECONDS,
            )
        except signing.SignatureExpired:
            return Response(
                {"success": False, "message": "Admin verification session expired. Sign in again."},
                status=status.HTTP_410_GONE,
            )
        except signing.BadSignature:
            return Response(
                {"success": False, "message": "Invalid admin verification session."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expected_device = str(payload.get("device_id") or "")
        supplied_device = str(request.headers.get("X-ARI-Device-ID", "") or "").strip()[:64]
        if expected_device and not constant_time_compare(expected_device, supplied_device):
            return Response(
                {"success": False, "message": "Admin verification must be completed on the same device."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user = User.objects.filter(
            pk=payload.get("user_id"),
            role="ADMIN",
            is_active=True,
        ).first()
        if user is None:
            return Response(
                {"success": False, "message": "Admin account is unavailable."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not constant_time_compare(
            str(payload.get("password_state") or ""),
            user.get_session_auth_hash(),
        ):
            return Response(
                {"success": False, "message": "Admin credentials changed. Sign in again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not check_password(otp, str(payload.get("otp_hash") or "")):
            return Response(
                {"success": False, "message": "Admin verification code is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Successful MFA challenges are single-use. cache.add() is atomic on
        # Django's supported production cache backends and prevents the same
        # signed challenge + OTP from minting additional sessions within its
        # five-minute validity window.
        replay_key = _mfa_replay_cache_key(payload)
        if not cache.add(replay_key, True, timeout=ADMIN_MFA_MAX_AGE_SECONDS):
            return Response(
                {
                    "success": False,
                    "message": "Admin verification code was already used. Sign in again.",
                },
                status=status.HTTP_409_CONFLICT,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "success": True,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class SecureChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = str(request.data.get("old_password") or "")
        new_password = str(request.data.get("new_password") or "")
        if not old_password or not new_password:
            return Response(
                {"success": False, "message": "Old and new password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        if not check_password(old_password, user.password):
            return Response(
                {"success": False, "message": "Old password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if old_password == new_password:
            return Response(
                {"success": False, "message": "New password must be different from the old password."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return Response(
                {"success": False, "message": " ".join(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        # The password-change signal blacklists every refresh token that existed
        # before this save. Issue exactly one fresh session for the current device.
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "success": True,
                "message": "Password changed securely. Other sessions have been signed out.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )
