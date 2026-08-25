import secrets

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from accounts.models import User, PhoneOTP


OTP_EXPIRY_MINUTES = 5


def generate_otp():

    return str(
        100000 + secrets.randbelow(900000)
    )


@transaction.atomic
def create_phone_otp(user):

    if user.role != "CUSTOMER":

        raise ValueError(
            "OTP is only available for customers."
        )

    if user.is_verified:

        raise ValueError(
            "Phone number is already verified."
        )

    # --------------------------------------------------------
    # INVALIDATE PREVIOUS OTPs
    # --------------------------------------------------------

    PhoneOTP.objects.filter(
        user=user,
        is_used=False,
    ).update(
        is_used=True,
    )

    # --------------------------------------------------------
    # CREATE NEW OTP
    # --------------------------------------------------------

    otp = generate_otp()

    phone_otp = PhoneOTP.objects.create(
        user=user,
        otp=otp,
        expires_at=(
            timezone.now()
            + timedelta(
                minutes=OTP_EXPIRY_MINUTES
            )
        ),
    )

    return phone_otp


def verify_phone_otp(user, otp_value):

    if user.role != "CUSTOMER":

        raise ValueError(
            "OTP verification is only available "
            "for customers."
        )

    if user.is_verified:

        raise ValueError(
            "Phone number is already verified."
        )

    # --------------------------------------------------------
    # GET ACTIVE OTP
    # --------------------------------------------------------
    #
    # We use a transaction only around the database
    # operation that needs locking.
    #
    # IMPORTANT:
    # Validation errors are raised AFTER the transaction
    # commits, otherwise attempts/is_used would rollback.
    # --------------------------------------------------------

    error_message = None
    verified_user = None

    with transaction.atomic():

        latest_otp = (
            PhoneOTP.objects
            .select_for_update()
            .filter(
                user=user,
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )

        if latest_otp is None:

            error_message = (
                "No active OTP found."
            )

        # ----------------------------------------------------
        # EXPIRY
        # ----------------------------------------------------

        elif timezone.now() >= latest_otp.expires_at:

            latest_otp.is_used = True

            latest_otp.save(
                update_fields=[
                    "is_used"
                ]
            )

            error_message = (
                "OTP has expired."
            )

        # ----------------------------------------------------
        # MAX ATTEMPTS
        # ----------------------------------------------------

        elif (
            latest_otp.attempts
            >= PhoneOTP.MAX_ATTEMPTS
        ):

            latest_otp.is_used = True

            latest_otp.save(
                update_fields=[
                    "is_used"
                ]
            )

            error_message = (
                "Maximum OTP attempts exceeded."
            )

        # ----------------------------------------------------
        # WRONG OTP
        # ----------------------------------------------------

        elif latest_otp.otp != str(otp_value):

            latest_otp.attempts += 1

            if (
                latest_otp.attempts
                >= PhoneOTP.MAX_ATTEMPTS
            ):

                latest_otp.is_used = True

            latest_otp.save(
                update_fields=[
                    "attempts",
                    "is_used",
                ]
            )

            error_message = (
                "Invalid OTP."
            )

        # ----------------------------------------------------
        # CORRECT OTP
        # ----------------------------------------------------

        else:

            latest_otp.is_used = True

            latest_otp.save(
                update_fields=[
                    "is_used"
                ]
            )

            user.is_verified = True

            user.save(
                update_fields=[
                    "is_verified"
                ]
            )

            verified_user = user

    # --------------------------------------------------------
    # IMPORTANT:
    # Raise AFTER atomic block.
    #
    # Database changes above have already committed.
    # --------------------------------------------------------

    if error_message:

        raise ValueError(
            error_message
        )

    return verified_user