from django.apps import AppConfig


class JobsConfig(AppConfig):
    name = 'jobs'

    def ready(self):
        # Register visual-parts passport models before loading signal handlers.
        from . import ro_parts_models  # noqa: F401
        from . import signals  # noqa: F401
        from . import ro_parts_signals  # noqa: F401
