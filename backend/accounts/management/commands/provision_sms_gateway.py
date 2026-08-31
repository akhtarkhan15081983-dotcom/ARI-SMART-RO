import hashlib
import secrets

from django.core.management.base import BaseCommand, CommandError

from accounts.models import SmsGatewayDevice


class Command(BaseCommand):
    help = "Provision or rotate credentials for an ARI office SMS gateway device."

    def add_arguments(self, parser):
        parser.add_argument("device_id")
        parser.add_argument("--name", default="ARI Office SMS Gateway")
        parser.add_argument("--phone", default="")
        parser.add_argument("--rotate", action="store_true")

    def handle(self, *args, **options):
        device_id = options["device_id"].strip()
        if not device_id or len(device_id) > 40:
            raise CommandError("device_id must contain 1-40 characters.")
        existing = SmsGatewayDevice.objects.filter(device_id=device_id).first()
        if existing is not None and not options["rotate"]:
            raise CommandError("Gateway already exists. Use --rotate to issue a new key.")
        raw_key = secrets.token_urlsafe(48)
        secret_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        device, _ = SmsGatewayDevice.objects.update_or_create(
            device_id=device_id,
            defaults={
                "name": options["name"].strip(),
                "phone_number": options["phone"].strip(),
                "secret_hash": secret_hash,
                "is_active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS("Gateway provisioned. Save this key now; it will not be shown again."))
        self.stdout.write(f"DEVICE_ID={device.device_id}")
        self.stdout.write(f"GATEWAY_KEY={raw_key}")
