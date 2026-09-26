import calendar
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from accounts.permissions import IsVerifiedCustomer, user_role
from .models import Customer, CustomerRentHistory
from .rent_policy import RENT_GRACE_DAYS, rent_penalty
from .views import CustomerListAPIView as BaseCustomerListAPIView, _sync_current_rent_offer


def _linked_customer(user):
    """Resolve the authenticated customer by the durable user relation first.

    Existing-customer activation can use an internal login identity when the
    registered mobile already belongs to a dormant account. Customer-facing
    APIs must therefore never rely on request.user.phone as the primary key.
    """
    customer = Customer.objects.filter(user=user, is_active=True).first()
    if customer is not None:
        return customer

    phone = str(getattr(user, "phone", "") or "").strip()
    if not phone:
        return None

    matches = list(
        Customer.objects.filter(
            phone=phone,
            is_active=True,
            user__isnull=True,
        ).order_by("id")[:2]
    )
    if len(matches) != 1:
        return None

    customer = matches[0]
    with transaction.atomic():
        locked = Customer.objects.select_for_update().get(pk=customer.pk)
        if locked.user_id is None:
            locked.user = user
            locked.save(update_fields=["user"])
        elif locked.user_id != user.id:
            return None
        return locked


class CustomerListAPIView(BaseCustomerListAPIView):
    """Keep operations behavior unchanged, but make customer self lookup durable."""

    def get_queryset(self):
        user = self.request.user
        if user_role(user) != "CUSTOMER":
            return super().get_queryset()
        customer = _linked_customer(user)
        if customer is None:
            return Customer.objects.none()
        return Customer.objects.filter(pk=customer.pk)


class CustomerRentAPIView(BaseCustomerListAPIView):
    permission_classes = [IsVerifiedCustomer]

    def get(self, request):
        if user_role(request.user) != "CUSTOMER":
            return Response(
                {"success": False, "message": "Only customers can access rent details."},
                status=status.HTTP_403_FORBIDDEN,
            )

        customer = _linked_customer(request.user)
        if customer is None:
            return Response(
                {"success": False, "message": "Customer account is not linked yet. Please sign in again."},
                status=status.HTTP_404_NOT_FOUND,
            )

        today = timezone.now().date()
        current_month = today.replace(day=1)

        rent_record, _ = CustomerRentHistory.objects.get_or_create(
            customer=customer,
            rent_month=current_month,
            defaults={
                "expected_rent": customer.monthly_rent,
                "paid_amount": 0,
            },
        )
        rent_record = _sync_current_rent_offer(customer, rent_record)

        expected = float(rent_record.expected_rent or 0)
        paid = float(rent_record.paid_amount or 0)
        balance = max(expected - paid, 0)

        if expected <= 0:
            payment_status = "NO_RENT"
        elif paid >= expected:
            payment_status = "PAID"
        elif paid > 0:
            payment_status = "PARTIAL"
        else:
            payment_status = "PENDING"

        installation_day = customer.installation_date.day if customer.installation_date else 1
        last_day = calendar.monthrange(today.year, today.month)[1]
        due_day = min(installation_day, last_day)
        due_date = date(today.year, today.month, due_day)
        penalty = rent_penalty(Decimal(str(balance)), due_date)

        history_data = []
        history = CustomerRentHistory.objects.filter(customer=customer).order_by("-rent_month", "-id")
        for item in history:
            item_expected = float(item.expected_rent or 0)
            item_paid = float(item.paid_amount or 0)
            item_balance = max(item_expected - item_paid, 0)
            if item_expected <= 0:
                item_status = "NO_RENT"
            elif item_paid >= item_expected:
                item_status = "PAID"
            elif item_paid > 0:
                item_status = "PARTIAL"
            else:
                item_status = "PENDING"
            history_data.append({
                "id": item.id,
                "rent_month": item.rent_month.isoformat() if item.rent_month else None,
                "expected_rent": item_expected,
                "paid_amount": item_paid,
                "balance": item_balance,
                "status": item_status,
                "raw_value": item.raw_value,
                "remarks": item.remarks,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            })

        return Response(
            {
                "success": True,
                "customer": {
                    "id": customer.id,
                    "customer_id": customer.customer_id,
                    "name": customer.name,
                    "phone": customer.phone,
                    "card_number": customer.card_number,
                },
                "ro": {
                    "model": customer.ro_model,
                    "installation_date": customer.installation_date.isoformat() if customer.installation_date else None,
                    "installation_charge": float(customer.installation_charge or 0),
                    "monthly_rent": float(customer.monthly_rent or 0),
                    "security_deposit": float(customer.security_deposit or 0),
                    "is_active": customer.is_active,
                },
                "current_rent": {
                    "id": rent_record.id,
                    "rent_month": current_month.isoformat(),
                    "base_rent": float(rent_record.base_rent or expected),
                    "discount_amount": float(rent_record.discount_amount or 0),
                    "applied_offer": (
                        {
                            "id": rent_record.applied_offer_id,
                            "title": rent_record.applied_offer.title,
                            "promo_code": rent_record.applied_offer.promo_code,
                        }
                        if rent_record.applied_offer_id else None
                    ),
                    "expected_rent": expected,
                    "paid_amount": paid,
                    "balance": balance,
                    "due_date": due_date.isoformat(),
                    "grace_days": RENT_GRACE_DAYS,
                    "penalty_days": penalty["penalty_days"],
                    "penalty_amount": float(penalty["penalty_amount"]),
                    "total_due": float(Decimal(str(balance)) + penalty["penalty_amount"]),
                    "status": payment_status,
                },
                "history": history_data,
            },
            status=status.HTTP_200_OK,
        )
