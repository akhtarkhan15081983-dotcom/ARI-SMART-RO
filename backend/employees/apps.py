from django.apps import AppConfig


class EmployeesConfig(AppConfig):
    name = 'employees'

    def ready(self):
        # Register shift GPS history model and the profile-save hook that
        # records every accepted live-location point without changing the
        # existing live-location API contract.
        from . import location_models  # noqa: F401
        from . import location_signals  # noqa: F401
