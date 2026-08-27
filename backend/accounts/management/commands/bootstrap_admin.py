import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create the initial administrator from environment variables."

    def handle(self, *args, **options):
        phone = os.getenv("DJANGO_BOOTSTRAP_ADMIN_PHONE", "").strip()
        password = os.getenv("DJANGO_BOOTSTRAP_ADMIN_PASSWORD", "")
        first_name = os.getenv("DJANGO_BOOTSTRAP_ADMIN_NAME", "Administrator").strip()

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
            self.stdout.write("Admin bootstrap skipped; the phone already exists.")
            return

        user.set_password(password)
        user.save(update_fields=["password"])
        self.stdout.write(self.style.SUCCESS("Initial administrator created."))
