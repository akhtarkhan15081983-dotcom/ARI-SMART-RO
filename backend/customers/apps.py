from django.apps import AppConfig


class CustomersConfig(AppConfig):
    name = "customers"

    def ready(self):
        from . import serializers
        from .security_serializers import HardenedCustomerProfileSerializer

        serializers.CustomerProfileSerializer = HardenedCustomerProfileSerializer
