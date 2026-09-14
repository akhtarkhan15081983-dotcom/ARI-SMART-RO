import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create the initial administrator from environment variables, or explicitly reset an existing admin."

    def handle(self, *args, **options):
        phone = os.getenv("DJANGO_BOOTSTRAP_ADMIN_PHONE", "").strip()
        password = os.getenv("DJANGO_BOOTSTRAP_ADMIN_PASSWORD", "")
        first_name = os.getenv("DJANGO_BOOTSTRAP_ADMIN_NAME", "Administrator").strip()
        reset_existing = os.getenv("DJANGO_BOOTSTRAP_ADMIN_RESET", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        if not phone and not password:
            self.stdout.write("Admin bootstrap skipped; credentials are not configured.")
            return
        if not phone or not password:
            raise CommandError("Both bootstrap admin phone and password must be configured.")
        if len(phone) != 10 or not phone.isdigit():
            raise CommandError("The bootstrap admin phone must contain exactly 10 digits.")
        if len(password) < 12:
            raise CommandError("The bootstrap admin password must contain at least 12 characters.")

        User = get_user_model()
        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={
                "first_name": first_name or "Administrator",
                "role": "ADMIN",
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
                "is_verified": True,
            },
        )

        if not created:
            if not reset_existing:
                self.stdout.write("Admin bootstrap skipped; the phone already exists.")
                return
            if not (getattr(user, "is_superuser", False) or getattr(user, "role", "") == "ADMIN"):
                raise CommandError("Refusing to reset a non-admin account.")

            user.set_password(password)
            update_fields = ["password"]

            if hasattr(user, "failed_login_attempts"):
                user.failed_login_attempts = 0
                update_fields.append("failed_login_attempts")
            if hasattr(user, "locked_until"):
                user.locked_until = None
                update_fields.append("locked_until")

            user.save(update_fields=update_fields)
            self.stdout.write(self.style.SUCCESS("Existing administrator password reset successfully."))
            return

        user.set_password(password)
        user.save(update_fields=["password"])
        self.stdout.write(self.style.SUCCESS("Initial administrator created."))
