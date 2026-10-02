from django.apps import AppConfig


class EmployeesConfig(AppConfig):
    name = 'employees'

    def ready(self):
        # Register shift GPS history model and the profile-save hook that
        # records every accepted live-location point without changing the
        # existing live-location API contract.
        from . import location_models  # noqa: F401
        from . import location_signals  # noqa: F401
        # Corporate HR lifecycle is intentionally kept as an additive model
        # layer so existing attendance/payroll/training contracts remain safe.
        from . import hr_lifecycle_models  # noqa: F401
        # Phase-1 READY FOR DUTY requires real uploaded, verified, valid files.
        from . import hr_phase1_compliance  # noqa: F401
