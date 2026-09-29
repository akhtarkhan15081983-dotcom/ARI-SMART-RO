from rest_framework.exceptions import ValidationError

from customers.models import Customer

from .models import Complaint
from .views import (
    ComplaintCreateAPIView,
    ComplaintDetailAPIView,
    ComplaintListAPIView,
    ComplaintSearchAPIView,
    restrict_complaints_for_user,
)


def linked_customer_for_complaints(user):
    if (
        not user
        or not user.is_authenticated
        or getattr(user, "role", None) != "CUSTOMER"
        or not user.is_verified
        or not user.is_active
    ):
        return None

    linked = Customer.objects.filter(user=user, is_active=True).first()
    if linked is not None:
        return linked

    legacy = (
        Customer.objects.filter(
            phone=user.phone,
            user__isnull=True,
            is_active=True,
        )
        .order_by("id")
        .first()
    )
    if legacy is not None:
        legacy.user = user
        legacy.save(update_fields=["user"])
    return legacy


def secure_complaint_queryset(queryset, user):
    if getattr(user, "role", None) == "CUSTOMER":
        customer = linked_customer_for_complaints(user)
        return queryset.filter(customer=customer) if customer is not None else queryset.none()
    return restrict_complaints_for_user(queryset, user)


class SecureComplaintListAPIView(ComplaintListAPIView):
    def get_queryset(self):
        queryset = Complaint.objects.select_related(
            "customer", "engineer__user", "linked_service"
        ).order_by("-id")
        return secure_complaint_queryset(queryset, self.request.user)


class SecureComplaintDetailAPIView(ComplaintDetailAPIView):
    def get_queryset(self):
        queryset = Complaint.objects.select_related(
            "customer", "engineer__user", "linked_service"
        )
        return secure_complaint_queryset(queryset, self.request.user)


class SecureComplaintSearchAPIView(ComplaintSearchAPIView):
    def get_queryset(self):
        keyword = self.request.GET.get("q", "").strip()
        queryset = secure_complaint_queryset(
            Complaint.objects.select_related(
                "customer", "engineer__user", "linked_service"
            ),
            self.request.user,
        )
        if keyword:
            from django.db.models import Q

            queryset = queryset.filter(
                Q(complaint_id__icontains=keyword)
                | Q(customer__name__icontains=keyword)
                | Q(customer__phone__icontains=keyword)
                | Q(description__icontains=keyword)
            )
        return queryset.order_by("-id")


class SecureComplaintCreateAPIView(ComplaintCreateAPIView):
    def perform_create(self, serializer):
        if getattr(self.request.user, "role", None) != "CUSTOMER":
            return super().perform_create(serializer)

        customer = linked_customer_for_complaints(self.request.user)
        if customer is None:
            raise ValidationError({
                "customer": ["Customer account is not linked to a customer record."]
            })
        serializer.save(
            customer=customer,
            engineer=None,
            priority="NORMAL",
            latitude=customer.latitude,
            longitude=customer.longitude,
        )
