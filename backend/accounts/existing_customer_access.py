import hmac
import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from customers.models import Customer

from .models import AuthSecurityEvent, User
from .serializers import UserSerializer
from .views import ProductionScopedRateThrottle

SALT = "ari-existing-customer-first-login-v1"
MAX_AGE_SECONDS = 600


def _digits(value):
    return re.sub(r"\D", "", str(value or ""))


def _phone(value):
    digits = _digits(value)
    return digits[-10:] if len(digits) >= 10 else digits


def _customer_for_identifier(identifier):
    value = str(identifier or "").strip()
    if not value:
        return None, "MISSING"

    # Exact customer/card reference always wins and stays unique.
    reference = Customer.objects.filter(is_active=True).filter(
        Q(customer_id__iexact=value)
        | Q(card_number__iexact=value)
        | Q(old_card_number__iexact=value)
    ).order_by("id")
    if reference.count() == 1:
        return reference.first(), None
    if reference.count() > 1:
        return None, "AMBIGUOUS"

    phone = _phone(value)
    if len(phone) != 10:
        return None, "NOT_FOUND"
    matches = Customer.objects.filter(is_active=True, phone=phone).order_by("id")
    if matches.count() == 1:
        return matches.first(), None
    if matches.count() > 1:
        return None, "AMBIGUOUS_PHONE"
    return None, "NOT_FOUND"


def _internal_phone(customer):
    real = _phone(customer.phone)
    if len(real) == 10 and not User.objects.filter(phone=real).exists():
        return real
    for prefix in ("0", "1", "2", "3", "4", "5"):
        candidate = f"{prefix}{customer.pk:09d}"
        if not User.objects.filter(phone=candidate).exists():
            return candidate
    raise RuntimeError("Unable to allocate customer login identity")


def _split_name(name):
    parts = str(name or "Customer").strip().split()
    return (parts[0][:100], " ".join(parts[1:])[:100]) if parts else ("Customer", "")


def _event(request, event_type, user=None, **details):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    AuthSecurityEvent.objects.create(
        user=user,
        event_type=event_type,
        ip_address=forwarded or request.META.get("REMOTE_ADDR") or None,
        device_id=str(request.headers.get("X-ARI-Device-ID", "") or "")[:64],
        details=details,
    )


def _tokens(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


class ExistingCustomerBootstrapAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ProductionScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        configured = str(getattr(settings, "EXISTING_CUSTOMER_TEMP_PASSWORD", "") or "")
        supplied = str(request.data.get("temporary_password") or "")
        if not configured:
            return Response({"success": False, "message": "Existing customer first login is not configured."}, status=503)
        if not hmac.compare_digest(configured, supplied):
            return Response({"success": False, "message": "Temporary password is incorrect."}, status=401)

        customer, error = _customer_for_identifier(request.data.get("identifier"))
        if customer is None:
            if error == "AMBIGUOUS_PHONE":
                message = "This mobile number is shared by multiple customers. Use Customer ID or Card Number."
            else:
                message = "Existing customer could not be matched. Use Customer ID, Card Number or registered mobile."
            return Response({"success": False, "code": error, "message": message}, status=404)

        if customer.user_id is not None:
            return Response(
                {"success": False, "code": "ALREADY_ACTIVATED", "message": "Account already activated. Login with your personal password."},
                status=409,
            )

        payload = {"customer_pk": customer.pk, "internal_phone": _internal_phone(customer)}
        token = signing.dumps(payload, salt=SALT, compress=True)
        return Response({
            "success": True,
            "activation_token": token,
            "expires_in_seconds": MAX_AGE_SECONDS,
            "customer": {
                "customer_id": customer.customer_id,
                "card_number": customer.card_number,
                "name": customer.name,
                "phone": _phone(customer.phone),
            },
            "message": "Existing customer verified. Create your personal password now.",
        })


class ExistingCustomerCompleteAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ProductionScopedRateThrottle]
    throttle_scope = "login"

    @transaction.atomic
    def post(self, request):
        token = str(request.data.get("activation_token") or "")
        new_password = str(request.data.get("new_password") or "")
        if not token or not new_password:
            return Response({"success": False, "message": "Activation session and new password are required."}, status=400)

        try:
            payload = signing.loads(token, salt=SALT, max_age=MAX_AGE_SECONDS)
        except signing.SignatureExpired:
            return Response({"success": False, "message": "First-login session expired. Start again."}, status=410)
        except signing.BadSignature:
            return Response({"success": False, "message": "Invalid first-login session."}, status=400)

        customer = Customer.objects.select_for_update().filter(pk=payload.get("customer_pk"), is_active=True).first()
        if customer is None:
            return Response({"success": False, "message": "Customer record is unavailable."}, status=404)
        if customer.user_id is not None:
            return Response({"success": False, "message": "Customer account is already activated."}, status=409)

        internal_phone = str(payload.get("internal_phone") or "")
        if User.objects.filter(phone=internal_phone).exists():
            internal_phone = _internal_phone(customer)
        first_name, last_name = _split_name(customer.name)
        prototype = User(phone=internal_phone, first_name=first_name, last_name=last_name, role="CUSTOMER")
        try:
            validate_password(new_password, user=prototype)
        except DjangoValidationError as exc:
            return Response({"success": False, "message": " ".join(exc.messages)}, status=400)

        configured = str(getattr(settings, "EXISTING_CUSTOMER_TEMP_PASSWORD", "") or "")
        if configured and hmac.compare_digest(configured, new_password):
            return Response({"success": False, "message": "Choose a personal password different from the temporary password."}, status=400)

        user = User.objects.create_user(
            phone=internal_phone,
            password=new_password,
            first_name=first_name,
            last_name=last_name,
            role="CUSTOMER",
            is_verified=True,
            is_active=True,
        )
        customer.user = user
        customer.save(update_fields=["user"])
        access, refresh = _tokens(user)
        _event(request, "LOGIN_SUCCESS", user=user, method="EXISTING_CUSTOMER_BOOTSTRAP", customer_id=customer.customer_id)
        return Response({
            "success": True,
            "message": "Account activated. Your personal password is now active.",
            "access": access,
            "refresh": refresh,
            "user": UserSerializer(user).data,
            "customer_id": customer.customer_id,
        }, status=201)


class ExistingCustomerReferenceLoginAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ProductionScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        customer, error = _customer_for_identifier(request.data.get("identifier"))
        password = str(request.data.get("password") or "")
        if customer is None or customer.user_id is None:
            message = "Use Customer ID or Card Number." if error == "AMBIGUOUS_PHONE" else "Customer account is not activated yet."
            return Response({"success": False, "message": message}, status=404)
        user = customer.user
        if not user.is_active or not user.is_verified or not user.check_password(password):
            if user.is_active:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 5:
                    user.locked_until = timezone.now() + timedelta(minutes=15)
                user.save(update_fields=["failed_login_attempts", "locked_until"])
            _event(request, "LOGIN_FAILED", user=user, method="CUSTOMER_REFERENCE")
            return Response({"success": False, "message": "Invalid customer login or password."}, status=401)
        if user.locked_until and user.locked_until > timezone.now():
            return Response({"success": False, "message": "Account is temporarily locked. Try again later."}, status=429)
        if user.failed_login_attempts or user.locked_until:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.save(update_fields=["failed_login_attempts", "locked_until"])
        access, refresh = _tokens(user)
        _event(request, "LOGIN_SUCCESS", user=user, method="CUSTOMER_REFERENCE", customer_id=customer.customer_id)
        return Response({
            "success": True,
            "access": access,
            "refresh": refresh,
            "user": UserSerializer(user).data,
            "customer_id": customer.customer_id,
        })
