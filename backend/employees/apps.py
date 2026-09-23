from django.apps import AppConfig


class EmployeesConfig(AppConfig):
    name = 'employees'

    def ready(self):
        # EmployeeDeviceHealth lives in a focused module to keep the production
        # hotfix isolated from the larger employee model file. Importing it here
        # ensures Django registers the model before migrations/checks run.
        from . import device_health  # noqa: F401
