from django.apps import AppConfig


class TenancyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tenancy"
    verbose_name = "SaaS Companies & Billing"

    def ready(self):
        from . import signals  # noqa: F401
        from .id_sequences import install_human_readable_id_hardening

        install_human_readable_id_hardening()
