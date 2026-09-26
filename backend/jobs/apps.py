from django.apps import AppConfig


class JobsConfig(AppConfig):
    name = 'jobs'

    def ready(self):
        # Register the visual-parts passport models and existing workflow signals.
        # The passport models live in a separate module to keep jobs/models.py stable.
        from . import ro_parts_models  # noqa: F401
        from . import signals  # noqa: F401
