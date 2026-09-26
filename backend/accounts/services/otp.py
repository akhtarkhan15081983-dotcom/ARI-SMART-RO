import base64
import secrets

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from accounts.models import User, PhoneOTP


OTP_EXPIRY_MINUTES = 5
OTP_FINGERPRINT_SALT = "ari-phone-otp-storage-v1"


def generate_otp():
    return str(100000 + secrets.randbelow(900000))


def _otp_fingerprint(value):
    """Return a keyed six-character database fingerprint for a short OTP."""
    digest = salted_hmac(
        OTP_FINGERPRINT_SALT,
        str(value),
        secret=settings.SECRET_KEY,
        algorithm="sha256",
    ).digest()
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return "h" + encoded[:5]


def _otp_matches(stored_value, candidate_value):
    stored = str(stored_value or "")
    candidate = str(candidate_value or "")

    if stored.startswith("h") and len(stored) == 6:
        return constant_time_compare(stored, _otp_fingerprint(candidate))

    # Backward compatibility for any OTP generated immediately before rollout.
    return constant_time_compare(stored, candidate)


@transaction.atomic
def create_phone_otp(user):
    if user.role != "CUSTOMER":
        raise ValueError("OTP is only available for customers.")

    if user.is_verified:
        raise ValueError("Phone number is already verified.")

    PhoneOTP.objects.filter(user=user, is_used=False).update(is_used=True)

    otp = generate_otp()
    stored_otp = otp if settings.DEBUG else _otp_fingerprint(otp)

    phone_otp = PhoneOTP.objects.create(
        user=user,
        otp=stored_otp,
        expires_at=timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )

    # Keep the real code in memory only long enough for the delivery layer.
    # Existing callers use ``phone_otp.otp`` directly, so expose the plaintext
    # on this Python object after the hashed value has already been persisted.
    phone_otp.delivery_otp = otp
    phone_otp.otp = otp
    return phone_otp


def verify_phone_otp(user, otp_value, new_password):
    if user.role != "CUSTOMER":
        raise ValueError("OTP verification is only available for customers.")

    if user.is_verified:
        raise ValueError("Phone number is already verified.")

    error_message = None
    verified_user = None

    with transaction.atomic():
        latest_otp = (
            PhoneOTP.objects.select_for_update()
            .filter(user=user, is_used=False)
            .order_by("-created_at")
            .first()
        )

        if latest_otp is None:
            error_message = "No active OTP found."

        elif timezone.now() >= latest_otp.expires_at:
            latest_otp.is_used = True
            latest_otp.save(update_fields=["is_used"])
            error_message = "OTP has expired."

        elif latest_otp.attempts >= PhoneOTP.MAX_ATTEMPTS:
            latest_otp.is_used = True
            latest_otp.save(update_fields=["is_used"])
            error_message = "Maximum OTP attempts exceeded."

        elif not _otp_matches(latest_otp.otp, otp_value):
            latest_otp.attempts += 1
            if latest_otp.attempts >= PhoneOTP.MAX_ATTEMPTS:
                latest_otp.is_used = True
            latest_otp.save(update_fields=["attempts", "is_used"])
            error_message = "Invalid OTP."

        else:
            latest_otp.is_used = True
            latest_otp.save(update_fields=["is_used"])

            user.is_verified = True
            user.is_active = True
            user.set_password(new_password)
            user.save(update_fields=["is_verified", "is_active", "password"])
            verified_user = user

    if error_message:
        raise ValueError(error_message)

    return verified_user
