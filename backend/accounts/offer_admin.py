from decimal import Decimal, InvalidOperation

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from customers.models import Customer

from .models import CustomerEngagement, NotificationCampaign
from .notifications import materialize_campaign
from .offer_audience import (
    OFFER_AUDIENCES,
    customer_user,
    users_for_customer_status,
)
from .permissions import IsAdmin


class AdminOfferCustomerAudienceAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        rows = Customer.objects.select_related("user").order_by("name", "id")[:5000]
        return Response({
            "customers": [
                {
                    "id": row.id,
                    "customer_id": row.customer_id,
                    "card_number": row.card_number,
                    "old_card_number": row.old_card_number,
                    "name": row.name,
                    "phone": row.phone,
                    "is_active": row.is_active,
                    "app_user_id": customer_user(row).id if customer_user(row) else None,
                }
                for row in rows
            ]
        })


class AdminOfferAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        rows = CustomerEngagement.objects.filter(kind="OFFER")[:100]
        return Response({
            "offers": [{
                "id": row.id,
                "title": row.title,
                "audience": row.audience,
                "target_user_id": row.target_user_id,
                "discount_type": row.discount_type,
                "discount_value": str(row.discount_value),
                "offer_scope": row.offer_scope,
                "auto_apply": row.auto_apply,
                "minimum_amount": str(row.minimum_amount),
                "max_discount": str(row.max_discount),
                "promo_code": row.promo_code,
                "valid_from": row.valid_from.isoformat(),
                "valid_until": row.valid_until.isoformat() if row.valid_until else None,
                "is_active": row.is_active,
            } for row in rows]
        })

    def post(self, request):
        title = str(request.data.get("title") or "").strip()
        message = str(request.data.get("message") or "").strip()
        if not title or not message:
            return Response({"detail": "Title and message are required."}, status=400)

        audience = str(request.data.get("audience") or "ALL").upper()
        if audience not in OFFER_AUDIENCES:
            return Response({
                "detail": "Offer audience must be ALL, ACTIVE, INACTIVE or TARGETED."
            }, status=400)

        target_user = None
        target_customer = None
        if audience == "TARGETED":
            target_customer = Customer.objects.select_related("user").filter(
                pk=request.data.get("target_customer_id")
            ).first()
            if target_customer is None:
                return Response({"detail": "Target customer not found."}, status=400)
            target_user = customer_user(target_customer)
            if target_user is None:
                return Response({
                    "detail": (
                        "This customer does not have an active customer-app login yet. "
                        "Link/register the customer app account before sending an in-app offer."
                    )
                }, status=400)

        discount_type = str(request.data.get("discount_type") or "NONE").upper()
        offer_scope = str(request.data.get("offer_scope") or "NONE").upper()
        action = str(request.data.get("action") or "NONE").upper()
        if discount_type not in {"PERCENT", "FIXED"}:
            return Response({"detail": "Discount type must be PERCENT or FIXED."}, status=400)
        if offer_scope not in {"RENT", "PURCHASE", "SERVICE", "AMC", "REFERRAL"}:
            return Response({"detail": "Select a valid offer scope."}, status=400)
        if action not in {choice[0] for choice in CustomerEngagement.ACTION_CHOICES}:
            return Response({"detail": "Invalid offer action."}, status=400)

        try:
            discount_value = Decimal(str(request.data.get("discount_value") or 0))
            max_discount = Decimal(str(request.data.get("max_discount") or 0))
            minimum_amount = Decimal(str(request.data.get("minimum_amount") or 0))
        except (InvalidOperation, ValueError, TypeError):
            return Response({"detail": "Discount amounts must be valid numbers."}, status=400)
        if discount_value <= 0:
            return Response({"detail": "Discount value must be greater than zero."}, status=400)
        if discount_type == "PERCENT" and discount_value > 100:
            return Response({"detail": "Percentage discount cannot exceed 100%."}, status=400)
        if max_discount < 0 or minimum_amount < 0:
            return Response({"detail": "Minimum amount and maximum discount cannot be negative."}, status=400)

        try:
            priority_value = int(request.data.get("priority") or 50)
        except (TypeError, ValueError):
            return Response({"detail": "Offer priority must be a number."}, status=400)
        priority_value = max(0, min(priority_value, 100))

        raw_auto_apply = request.data.get("auto_apply", False)
        auto_apply = (
            raw_auto_apply
            if isinstance(raw_auto_apply, bool)
            else str(raw_auto_apply).strip().lower() in {"1", "true", "yes", "on"}
        )

        valid_until = None
        raw_valid_until = request.data.get("valid_until")
        if raw_valid_until:
            try:
                valid_until = timezone.datetime.fromisoformat(str(raw_valid_until))
                if timezone.is_naive(valid_until):
                    valid_until = timezone.make_aware(valid_until)
            except ValueError:
                return Response({"detail": "Invalid valid_until."}, status=400)

        offer = CustomerEngagement.objects.create(
            kind="OFFER",
            audience=audience,
            target_user=target_user,
            title=title[:120],
            message=message[:500],
            badge_text=str(request.data.get("badge_text") or "").strip()[:30],
            discount_type=discount_type,
            discount_value=discount_value,
            promo_code=str(request.data.get("promo_code") or "").strip()[:30],
            offer_scope=offer_scope,
            auto_apply=auto_apply,
            max_discount=max_discount,
            minimum_amount=minimum_amount,
            terms=str(request.data.get("terms") or "").strip()[:300],
            valid_until=valid_until,
            priority=priority_value,
            action=action,
            action_label=str(request.data.get("action_label") or "").strip()[:40],
            created_by=request.user,
        )

        campaign = NotificationCampaign.objects.create(
            title=offer.title,
            message=offer.message,
            category="OFFER",
            priority="HIGH" if offer.priority >= 75 else "NORMAL",
            audience="USERS",
            action=offer.action,
            action_label=offer.action_label,
            valid_until=offer.valid_until,
            created_by=request.user,
        )

        if audience == "TARGETED":
            recipient_users = [target_user]
        elif audience == "ACTIVE":
            recipient_users = list(users_for_customer_status(True))
        elif audience == "INACTIVE":
            recipient_users = list(users_for_customer_status(False))
        else:
            recipient_users = list(
                users_for_customer_status(True).union(users_for_customer_status(False))
            )

        campaign.target_users.set([user for user in recipient_users if user is not None])
        delivered = materialize_campaign(campaign)

        return Response({
            "id": offer.id,
            "notification_campaign_id": campaign.id,
            "audience": audience,
            "target_customer_id": target_customer.id if target_customer else None,
            "eligible_app_users": len(recipient_users),
            "delivered": delivered,
            "detail": "Offer created and sent to eligible customer inboxes.",
        }, status=201)
