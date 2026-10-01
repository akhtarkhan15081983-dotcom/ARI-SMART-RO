from rest_framework import generics

from accounts.permissions import CanEditCustomer

from .edit_serializers import CustomerStaffEditSerializer
from .models import Customer
from .tenant_scope import operator_customer_queryset


class CustomerUpdateAPIView(generics.UpdateAPIView):
    """Edit customer operational details while keeping core IDs immutable."""

    queryset = Customer.objects.all()
    serializer_class = CustomerStaffEditSerializer
    permission_classes = [CanEditCustomer]

    def get_queryset(self):
        return operator_customer_queryset(
            self.request,
            Customer.objects.all(),
        )
