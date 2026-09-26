from rest_framework import generics

from accounts.permissions import CanEditCustomer

from .edit_serializers import CustomerStaffEditSerializer
from .models import Customer


class CustomerUpdateAPIView(generics.UpdateAPIView):
    """Edit customer operational details while keeping core IDs immutable."""

    queryset = Customer.objects.all()
    serializer_class = CustomerStaffEditSerializer
    permission_classes = [CanEditCustomer]
