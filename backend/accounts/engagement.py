from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from customers.models import CustomerRentHistory
from customers.rent_policy import rent_alert_schedule, rent_due_date, rent_penalty
from .models import CustomerEngagement, CustomerEngagementRead


def _discount_label(item):
    if item.discount_type == "PERCENT":
        return f"{item.discount_value.normalize()}% OFF"
    if item.discount_type == "FIXED":
        return f"₹{item.discount_value.quantize(Decimal('1'))} OFF"
    return ""


def _decimal_string(value):
    """Return a compact decimal string without unnecessary trailing zeroes."""
    normalized = Decimal(value).normalize()
    return format(normalized, "f")


class CustomerEngagementAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        now = timezone.now()
        items = CustomerEngagement.objects.filter(
            is_active=True, valid_from__lte=now,
        ).filter(
            Q(valid_until__isnull=True) | Q(valid_until__gte=now),
        )
        if request.user.is_authenticated:
            items = items.filter(
                Q(audience="ALL", target_user__isnull=True) |
                Q(audience="TARGETED", target_user=request.user),
            )
            read_ids = set(request.user.engagement_reads.values_list("engagement_id", flat=True))
        else:
            items = items.filter(audience="ALL", target_user__isnull=True)
            read_ids = set()
        payload = [{
            "id": item.id,
            "kind": item.kind,
            "title": item.title,
            "message": item.message,
            "badge": item.badge_text or _discount_label(item),
            "discount_type": item.discount_type,
            "discount_value": str(item.discount_value),
            "promo_code": item.promo_code,
            "terms": item.terms,
            "valid_until": item.valid_until.isoformat() if item.valid_until else None,
            "action": item.action,
            "action_label": item.action_label,
            "is_read": item.id in read_ids,
        } for item in items[:20]]

        payment_alert = None
        customer = getattr(request.user, "customer_profile", None) if request.user.is_authenticated else None
        if customer is not None:
            today = timezone.localdate()
            current_month = today.replace(day=1)
            outstanding = list(CustomerRentHistory.objects.filter(
                customer=customer, rent_month__lte=current_month,
                paid_amount__lt=models.F("expected_rent"),
            ).order_by("rent_month"))
            balance = sum(
                (max(Decimal("0"), row.expected_rent - row.paid_amount) for row in outstanding),
                Decimal("0"),
            )
            penalty_amount = Decimal("0")
            penalty_days = 0
            for row in outstanding:
                policy = rent_penalty(
                    row.expected_rent - row.paid_amount,
                    rent_due_date(customer, row.rent_month),
                    today,
                )
                penalty_amount += policy["penalty_amount"]
                penalty_days += policy["penalty_days"]

            current_due_date = rent_due_date(customer, current_month)
            schedule = rent_alert_schedule(current_due_date, now)
            current_record = next(
                (row for row in outstanding if row.rent_month == current_month),
                None,
            )
            should_alert = balance > 0 and (
                schedule["active"] or current_due_date < today or current_record is None
            )
            if should_alert:
                total_due = balance + penalty_amount
                oldest = outstanding[0].rent_month if outstanding else None
                payment_alert = {
                    "amount_due": _decimal_string(balance),
                    "rent_penalty": _decimal_string(penalty_amount),
                    "total_due": _decimal_string(total_due),
                    "penalty_days": penalty_days,
                    "oldest_due_month": oldest.isoformat() if oldest else None,
                    "due_date": current_due_date.isoformat(),
                    "title": "Rent payment reminder" if today <= current_due_date else "Rent payment overdue",
                    "message": (
                        f"₹{total_due.quantize(Decimal('1'))} is due including "
                        f"₹{penalty_amount.quantize(Decimal('1'))} late penalty."
                        if penalty_amount else
                        f"₹{balance.quantize(Decimal('1'))} rent is due on {current_due_date:%d %b}."
                    ),
                    "action": "RENT",
                    "action_label": "PAY / VIEW RENT",
                    "repeat_interval_hours": schedule["repeat_interval_hours"],
                    "next_alert_at": schedule["next_alert_at"].isoformat() if schedule["next_alert_at"] else None,
                }

        return Response({
            "items": payload,
            "payment_alert": payment_alert,
            "unread_count": sum(not item["is_read"] for item in payload) + (1 if payment_alert else 0),
        })

    def post(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Login required."}, status=401)
        engagement_id = request.data.get("engagement_id")
        if not engagement_id:
            return Response({"detail": "engagement_id is required."}, status=400)
        eligible = CustomerEngagement.objects.filter(id=engagement_id).filter(
            Q(audience="ALL", target_user__isnull=True) |
            Q(audience="TARGETED", target_user=request.user),
        ).first()
        if eligible is None:
            return Response({"detail": "Alert not found."}, status=404)
        CustomerEngagementRead.objects.get_or_create(engagement=eligible, user=request.user)
        return Response({"detail": "Marked as read."})
