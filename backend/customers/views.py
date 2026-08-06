from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Customer
from .serializers import CustomerSerializer


class CustomerListAPIView(generics.ListAPIView):

    serializer_class = CustomerSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        user = self.request.user

        # Admin & Manager
        if user.role in ["ADMIN", "MANAGER"]:
            return Customer.objects.all().order_by("-id")

        # Engineer
        elif user.role == "ENGINEER":
            return Customer.objects.filter(
                assigned_engineer__user=user
            ).order_by("-id")

        # Customer
        elif user.role == "CUSTOMER":
            return Customer.objects.filter(
                phone=user.phone
            )

        return Customer.objects.none()