import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class SMSDeliveryError(RuntimeError):
    pass


# Test/development-only delivery sink. OTPs are never printed to logs.
memory_outbox = []


def _international_phone(phone):
    digits = "".join(character for character in str(phone) if character.isdigit())
    country_code = str(settings.OTP_SMS_COUNTRY_CODE).lstrip("+")
    if digits.startswith(country_code):
        return digits
    return f"{country_code}{digits}"


def _send_msg91(phone, otp):
    query = urlencode({
        "template_id": settings.MSG91_TEMPLATE_ID,
        "mobile": _international_phone(phone),
        "authkey": settings.MSG91_AUTH_KEY,
        "otp": otp,
    })
    request = Request(
        f"https://control.msg91.com/api/v5/otp?{query}",
        method="POST",
        headers={"Accept": "application/json"},
    )
    with urlopen(request, timeout=settings.OTP_SMS_TIMEOUT_SECONDS) as response:
        if not 200 <= response.status < 300:
            raise SMSDeliveryError("MSG91 rejected the OTP delivery request.")


def _send_webhook(phone, otp):
    payload = json.dumps({
        "phone": _international_phone(phone),
        "otp": otp,
        "purpose": "customer_phone_verification",
        "message": f"Your ARI SMART RO verification code is {otp}. It expires in 5 minutes.",
    }).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if settings.OTP_SMS_WEBHOOK_TOKEN:
        headers["Authorization"] = f"Bearer {settings.OTP_SMS_WEBHOOK_TOKEN}"
    request = Request(
        settings.OTP_SMS_WEBHOOK_URL,
        data=payload,
        method="POST",
        headers=headers,
    )
    with urlopen(request, timeout=settings.OTP_SMS_TIMEOUT_SECONDS) as response:
        if not 200 <= response.status < 300:
            raise SMSDeliveryError("The SMS webhook rejected the OTP delivery request.")


def send_customer_verification_otp(phone, otp):
    backend = settings.OTP_SMS_BACKEND
    try:
        if backend == "memory":
            memory_outbox.append({"phone": str(phone), "otp": str(otp)})
            return
        if backend == "msg91":
            _send_msg91(phone, otp)
            return
        if backend == "webhook":
            _send_webhook(phone, otp)
            return
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise SMSDeliveryError("OTP delivery failed. Please try again.") from exc

    raise SMSDeliveryError("No supported SMS backend is configured.")
