from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Import customers from Excel file"

    def add_arguments(self, parser):
        parser.add_argument(
            "excel_file",
            type=str,
            help="Path of Excel file",
        )

    def handle(self, *args, **options):
        excel_file = options["excel_file"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Excel File Selected : {excel_file}"
            )
        )