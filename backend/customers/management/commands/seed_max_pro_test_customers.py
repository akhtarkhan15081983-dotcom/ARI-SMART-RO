from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from customers.models import Customer
from products.models import ROModel
from tenancy.models import Company


TEST_BATCH = "MAX_PRO_CERTIFICATION"
TEST_PHONE_BASE = 9199001000


class Command(BaseCommand):
    help = (
        "Create 5-10 deterministic Max-Pro customer accounts in an explicitly selected "
        "test/staging company. Dry-run unless --apply is supplied."
    )

    def add_arguments(self, parser):
        parser.add_argument("--company", required=True, help="Target Company.slug")
        parser.add_argument("--count", type=int, default=8, help="Number of test customers (5-10)")
        parser.add_argument(
            "--password",
            default="",
            help="Known password to set for the test customer accounts (required with --apply)",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write the test users/customers. Without this flag the command is read-only.",
        )

    def handle(self, *args, **options):
        count = int(options["count"])
        if count < 5 or count > 10:
            raise CommandError("--count must be between 5 and 10.")

        try:
            company = Company.objects.get(slug=options["company"])
        except Company.DoesNotExist as exc:
            raise CommandError("Target company was not found.") from exc

        shop_models = list(
            ROModel.objects.filter(is_active=True)
            .select_related("category")
            .order_by("category__name", "model_name", "id")
        )
        if not shop_models:
            raise CommandError("No active Shop RO models exist; seed products first.")

        plan = []
        for offset in range(1, count + 1):
            ro_model = shop_models[(offset - 1) % len(shop_models)]
            phone = str(TEST_PHONE_BASE + offset)
            rental = bool(ro_model.available_for_rent and offset % 2 == 0)
            plan.append(
                {
                    "phone": phone,
                    "name": f"MaxPro Test Customer {offset:02d}",
                    "ro": ro_model,
                    "ownership": "RENTAL" if rental else "PURCHASE",
                }
            )

        if not options["apply"]:
            self.stdout.write(self.style.WARNING("DRY RUN ONLY — no rows were changed."))
            self.stdout.write(f"Company: {company.slug} | Customers planned: {count}")
            for row in plan:
                self.stdout.write(
                    f"{row['phone']} | {row['name']} | {row['ro'].model_name} | {row['ownership']}"
                )
            return

        password = str(options["password"] or "")
        if len(password) < 10:
            raise CommandError("--password is required with --apply and must be at least 10 characters.")

        created_users = 0
        created_customers = 0
        updated_customers = 0

        with transaction.atomic():
            for index, row in enumerate(plan, start=1):
                phone = row["phone"]
                existing_user = User.objects.filter(phone=phone).first()
                if existing_user is not None and existing_user.role != "CUSTOMER":
                    raise CommandError(
                        f"Reserved test phone {phone} belongs to a non-customer account; aborting."
                    )

                user, user_created = User.objects.get_or_create(
                    phone=phone,
                    defaults={
                        "first_name": "MaxPro",
                        "last_name": f"Test {index:02d}",
                        "role": "CUSTOMER",
                        "is_verified": True,
                        "is_active": True,
                    },
                )
                if user_created:
                    created_users += 1
                user.first_name = "MaxPro"
                user.last_name = f"Test {index:02d}"
                user.role = "CUSTOMER"
                user.is_verified = True
                user.is_active = True
                user.set_password(password)
                user.save(
                    update_fields=[
                        "first_name",
                        "last_name",
                        "role",
                        "is_verified",
                        "is_active",
                        "password",
                    ]
                )

                ro_model = row["ro"]
                rental = row["ownership"] == "RENTAL"
                customer_defaults = {
                    "company": company,
                    "name": row["name"],
                    "phone": phone,
                    "email": "",
                    "address": f"Max-Pro certification test address {index}",
                    "area": "TEST DATA",
                    "city": company.city or "Test City",
                    "state": company.state or "Test State",
                    "pincode": company.pincode or "000000",
                    "ro_model": ro_model.model_name,
                    "installation_charge": ro_model.installation_charge,
                    "monthly_rent": ro_model.monthly_rent if rental else 0,
                    "security_deposit": ro_model.security_deposit if rental else 0,
                    "ownership_type": row["ownership"],
                    "installation_date": timezone.localdate(),
                    "is_active": True,
                    "import_batch": TEST_BATCH,
                    "legacy_source_sheet": "MAX_PRO_TEST",
                    "legacy_reference": f"MAXPRO-{index:02d}",
                    "legacy_remarks": "Synthetic certification data; never treat as a real customer.",
                }
                customer, customer_created = Customer.objects.update_or_create(
                    user=user,
                    defaults=customer_defaults,
                )
                if customer_created:
                    created_customers += 1
                else:
                    updated_customers += 1

        self.stdout.write(
            self.style.SUCCESS(
                "MAX-PRO TEST DATA READY | "
                f"users_created={created_users} customers_created={created_customers} "
                f"customers_updated={updated_customers} total={count}"
            )
        )
        self.stdout.write(
            "Login phones: " + ", ".join(row["phone"] for row in plan)
        )
        self.stdout.write("All seeded accounts use the operator-supplied --password value.")
