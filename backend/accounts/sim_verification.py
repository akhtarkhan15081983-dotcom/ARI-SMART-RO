import hashlib
import hmac
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from customers.models import Customer

from .models import (
    AuthSecurityEvent,
    SimVerificationChallenge,
    SmsGatewayDevice,
    SmsGatewaySubmission,
    User,
)
from .permissions import IsAdmin
from .serializers import UserSerializer
from .views import ProductionScopedRateThrottle


TOKEN_TTL_MINUTES = 5


def _digest(value):
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _phone(value):
    digits = re.sub(r"\D", "", str(value or ""))
    return digits[-10:] if len(digits) >= 10 else digits


def _active_gateway_phone():
    gateway = (
        SmsGatewayDevice.objects
        .filter(is_active=True)
        .exclude(phone_number="")
        .order_by("-created_at")
        .first()
    )
    if gateway is not None:
        return gateway.phone_number
    return str(getattr(settings, "ARI_SMS_GATEWAY_NUMBER", "")).strip()


class AdminSmsGatewaySetupAPIView(APIView):
    """Provision one office Android phone as the no-provider SIM SMS gateway."""

    permission_classes = [IsAdmin]

    def get(self, request):
        gateway = (
            SmsGatewayDevice.objects
            .filter(is_active=True)
            .order_by("-created_at")
            .first()
        )
        if gateway is None:
            return Response({"configured": False, "gateway": None})
        return Response({
            "configured": True,
            "gateway": {
                "device_id": gateway.device_id,
                "name": gateway.name,
                "phone_number": gateway.phone_number,
                "last_seen_at": gateway.last_seen_at,
                "created_at": gateway.created_at,
            },
        })

    @transaction.atomic
    def post(self, request):
        phone_number = _phone(request.data.get("phone_number"))
        if len(phone_number) != 10 or not phone_number.isdigit():
            return Response(
                {"success": False, "message": "Enter the 10-digit SIM number installed in this office Android phone."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        name = str(request.data.get("name") or "ARI Office SMS Gateway").strip()[:100]
        if not name:
            name = "ARI Office SMS Gateway"

        # Only one receiver should be active at a time. Re-provisioning rotates
        # credentials immediately so a lost/replaced office phone cannot submit.
        SmsGatewayDevice.objects.filter(is_active=True).update(is_active=False)

        api_key = secrets.token_urlsafe(32)
        gateway = SmsGatewayDevice.objects.create(
            device_id=f"ARI-GW-{secrets.token_hex(8).upper()}",
            name=name,
            secret_hash=_digest(api_key),
            phone_number=phone_number,
            is_active=True,
        )
        return Response(
            {
                "success": True,
                "message": "This phone is now the active ARI SIM verification gateway.",
                "gateway": {
                    "device_id": gateway.device_id,
                    "name": gateway.name,
                    "phone_number": gateway.phone_number,
                    # Returned once so the Android app can store it locally.
                    "api_key": api_key,
                },
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request):
        updated = SmsGatewayDevice.objects.filter(is_active=True).update(is_active=False)
        return Response({"success": True, "disabled": updated})


class SimVerificationStartAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ProductionScopedRateThrottle]
    throttle_scope = "sim_start"

    @transaction.atomic
    def post(self, request):
        phone = _phone(request.data.get("phone"))
        user = User.objects.select_for_update().filter(phone=phone, role="CUSTOMER").first()
        if user is None:
            return Response({"success": False, "message": "Create your customer account first."}, status=404)
        if user.is_verified:
            return Response({"success": False, "message": "Mobile number is already verified. Please login."}, status=400)
        office_number = _active_gateway_phone()
        if not office_number:
            return Response({"success": False, "message": "SIM verification gateway is not configured."}, status=503)
        password = str(request.data.get("new_password") or "")
        try:
            validate_password(password, user=user)
        except DjangoValidationError as exc:
            return Response({"success": False, "message": " ".join(exc.messages)}, status=400)

        SimVerificationChallenge.objects.filter(user=user, status="PENDING").update(status="CANCELLED")
        token = secrets.token_hex(4).upper()
        poll_secret = secrets.token_urlsafe(32)
        challenge = SimVerificationChallenge.objects.create(
            user=user,
            token_hash=_digest(token),
            poll_secret_hash=_digest(poll_secret),
            pending_password_hash=make_password(password),
            expires_at=timezone.now() + timedelta(minutes=TOKEN_TTL_MINUTES),
        )
        return Response({
            "success": True,
            "challenge_id": challenge.id,
            "poll_secret": poll_secret,
            "destination_number": office_number,
            "sms_body": f"ARI VERIFY {token}",
            "expires_in_seconds": TOKEN_TTL_MINUTES * 60,
        }, status=201)


class SimVerificationPollAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ProductionScopedRateThrottle]
    throttle_scope = "sim_poll"

    def post(self, request):
        challenge = SimVerificationChallenge.objects.select_related("user").filter(pk=request.data.get("challenge_id")).first()
        supplied = _digest(request.data.get("poll_secret", ""))
        if challenge is None or not hmac.compare_digest(challenge.poll_secret_hash, supplied):
            return Response({"success": False, "message": "Invalid verification session."}, status=404)
        if challenge.status == "PENDING" and challenge.expires_at <= timezone.now():
            challenge.status = "EXPIRED"
            challenge.save(update_fields=["status"])
        if challenge.status != "VERIFIED":
            return Response({"success": True, "status": challenge.status})

        user = challenge.user
        refresh = RefreshToken.for_user(user)
        return Response({
            "success": True,
            "status": "VERIFIED",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
            "existing_customer_linked": Customer.objects.filter(user=user).exists(),
        })


class SmsGatewayIngestAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "sms_gateway"

    @transaction.atomic
    def post(self, request):
        device_id = request.headers.get("X-ARI-Gateway-ID", "")
        api_key = request.headers.get("X-ARI-Gateway-Key", "")
        nonce = request.headers.get("X-ARI-Nonce", "")[:64]
        timestamp_value = request.headers.get("X-ARI-Timestamp", "")
        gateway = SmsGatewayDevice.objects.select_for_update().filter(device_id=device_id, is_active=True).first()
        if gateway is None or not hmac.compare_digest(gateway.secret_hash, _digest(api_key)):
            return Response({"success": False, "message": "Gateway authentication failed."}, status=401)
        try:
            request_time = int(timestamp_value)
        except (TypeError, ValueError):
            return Response({"success": False, "message": "Invalid gateway timestamp."}, status=400)
        if abs(int(timezone.now().timestamp()) - request_time) > 300 or not nonce:
            return Response({"success": False, "message": "Expired gateway request."}, status=400)
        if SmsGatewaySubmission.objects.filter(nonce=nonce).exists():
            return Response({"success": False, "message": "Duplicate gateway request."}, status=409)

        sender = _phone(request.data.get("sender_phone"))
        message = str(request.data.get("message", "")).strip().upper()
        match = re.fullmatch(r"ARI\s+VERIFY\s+([A-F0-9]{8})", message)
        result_code = "INVALID_FORMAT"
        accepted = False
        challenge = None
        if match:
            challenge = SimVerificationChallenge.objects.select_for_update().select_related("user").filter(
                token_hash=_digest(match.group(1)), status="PENDING", expires_at__gt=timezone.now()
            ).first()
            if challenge is None:
                result_code = "TOKEN_NOT_FOUND"
            elif _phone(challenge.user.phone) != sender:
                result_code = "SENDER_MISMATCH"
                challenge = None
            else:
                accepted = True
                result_code = "VERIFIED"

        SmsGatewaySubmission.objects.create(
            gateway=gateway,
            nonce=nonce,
            sender_phone=sender,
            message_fingerprint=_digest(message),
            accepted=accepted,
            result_code=result_code,
        )
        gateway.last_seen_at = timezone.now()
        gateway.save(update_fields=["last_seen_at"])

        if challenge is not None:
            user = challenge.user
            user.is_verified = True
            if challenge.pending_password_hash:
                user.password = challenge.pending_password_hash
                user.save(update_fields=["is_verified", "password"])
            else:
                user.save(update_fields=["is_verified"])
            customer = Customer.objects.select_for_update().filter(phone=user.phone).first()
            if customer is not None and customer.user_id in (None, user.id):
                customer.user = user
                customer.save(update_fields=["user"])
            challenge.status = "VERIFIED"
            challenge.verified_at = timezone.now()
            challenge.verified_by = gateway
            challenge.save(update_fields=["status", "verified_at", "verified_by"])
            AuthSecurityEvent.objects.create(user=user, event_type="OTP_VERIFIED", device_id=gateway.device_id, details={"method": "SIM_SMS"})

        return Response({"success": True, "accepted": accepted, "result_code": result_code})
