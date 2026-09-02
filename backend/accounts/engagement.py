from decimal import Decimal

from django.db import models
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from customers.models import CustomerRentHistory
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
            due = CustomerRentHistory.objects.filter(
                customer=customer, rent_month__lte=timezone.localdate(),
            ).aggregate(
                expected=Coalesce(Sum("expected_rent"), Decimal("0")),
                paid=Coalesce(Sum("paid_amount"), Decimal("0")),
            )
            balance = max(Decimal("0"), due["expected"] - due["paid"])
            if balance > 0:
                oldest = CustomerRentHistory.objects.filter(
                    customer=customer, rent_month__lte=timezone.localdate(),
                    paid_amount__lt=models.F("expected_rent"),
                ).order_by("rent_month").values_list("rent_month", flat=True).first()
                payment_alert = {
                    "amount_due": _decimal_string(balance),
                    "oldest_due_month": oldest.isoformat() if oldest else None,
                    "title": "Rent payment due",
                    "message": f"₹{balance.quantize(Decimal('1'))} is pending on your ARI account.",
                    "action": "RENT",
                    "action_label": "PAY / VIEW RENT",
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