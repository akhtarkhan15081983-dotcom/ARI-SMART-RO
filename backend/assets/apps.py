from django.apps import AppConfig


class AssetsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "assets"

    def ready(self):
        import assets.admin  # noqa: F401
        import assets.signals  # noqa: F401
