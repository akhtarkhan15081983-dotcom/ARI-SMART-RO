from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    CustomerEngagement,
    NotificationCampaign,
    User,
    UserNotification,
)
from .permissions import IsAdmin
from .system_notifications import sync_system_notifications


def _active_notifications(user):
    now = timezone.now()
    return UserNotification.objects.filter(user=user).filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=now)
    )


def _campaign_recipients(campaign):
    users = User.objects.filter(is_active=True)
    if campaign.audience == "CUSTOMERS":
        users = users.filter(role="CUSTOMER")
    elif campaign.audience == "EMPLOYEES":
        users = users.exclude(role="CUSTOMER")
    elif campaign.audience == "ROLE":
        users = users.filter(role=campaign.target_role)
    elif campaign.audience == "USERS":
        return campaign.target_users.filter(is_active=True)
    return users


def materialize_campaign(campaign):
    recipients = _campaign_recipients(campaign)
    existing = set(
        UserNotification.objects.filter(campaign=campaign).values_list("user_id", flat=True)
    )
    rows = [
        UserNotification(
            campaign=campaign,
            user=user,
            event_key=f"campaign:{campaign.id}",
            title=campaign.title,
            message=campaign.message,
            category=campaign.category,
            priority=campaign.priority,
            action=campaign.action,
            action_label=campaign.action_label,
            valid_until=campaign.valid_until,
        )
        for user in recipients.iterator()
        if user.id not in existing
    ]
    if rows:
        UserNotification.objects.bulk_create(rows, batch_size=500)
    return len(rows)


class NotificationCenterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sync_system_notifications(request.user)
        rows = _active_notifications(request.user)
        payload = [{
            "id": row.id,
            "title": row.title,
            "message": row.message,
            "category": row.category,
            "priority": row.priority,
            "action": row.action,
            "action_label": row.action_label,
            "is_read": row.is_read,
            "valid_until": row.valid_until.isoformat() if row.valid_until else None,
            "metadata": row.metadata,
            "created_at": row.created_at.isoformat(),
        } for row in rows[:200]]
        return Response({
            "items": payload,
            "unread_count": rows.filter(is_read=False).count(),
        })

    def post(self, request):
        notification_id = request.data.get("notification_id")
        mark_all = bool(request.data.get("mark_all", False))
        now = timezone.now()
        if mark_all:
            _active_notifications(request.user).filter(is_read=False).update(
                is_read=True, read_at=now
            )
            return Response({"detail": "All notifications marked as read."})
        row = _active_notifications(request.user).filter(pk=notification_id).first()
        if row is None:
            return Response({"detail": "Notification not found."}, status=404)
        if not row.is_read:
            row.is_read = True
            row.read_at = now
            row.save(update_fields=["is_read", "read_at"])
        return Response({"detail": "Notification marked as read."})


class AdminNotificationCampaignAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        rows = NotificationCampaign.objects.all()[:100]
        return Response({
            "campaigns": [{
                "id": row.id,
                "title": row.title,
                "category": row.category,
                "priority": row.priority,
                "audience": row.audience,
                "target_role": row.target_role,
                "action": row.action,
                "valid_until": row.valid_until.isoformat() if row.valid_until else None,
                "is_active": row.is_active,
                "delivery_count": row.deliveries.count(),
                "unread_count": row.deliveries.filter(is_read=False).count(),
                "created_at": row.created_at.isoformat(),
            } for row in rows]
        })

    def post(self, request):
        audience = str(request.data.get("audience") or "ALL").upper()
        target_role = str(request.data.get("target_role") or "").upper()
        allowed_audiences = {choice[0] for choice in NotificationCampaign.AUDIENCE_CHOICES}
        if audience not in allowed_audiences:
            return Response({"detail": "Invalid audience."}, status=400)
        if audience == "ROLE" and target_role not in {choice[0] for choice in User.ROLE_CHOICES}:
            return Response({"detail": "Valid target role is required."}, status=400)
        title = str(request.data.get("title") or "").strip()
        message = str(request.data.get("message") or "").strip()
        if not title or not message:
            return Response({"detail": "Title and message are required."}, status=400)

        category = str(request.data.get("category") or "GENERAL").upper()
        priority = str(request.data.get("priority") or "NORMAL").upper()
        action = str(request.data.get("action") or "NONE").upper()
        if category not in {choice[0] for choice in NotificationCampaign.CATEGORY_CHOICES}:
            return Response({"detail": "Invalid notification category."}, status=400)
        if priority not in {choice[0] for choice in NotificationCampaign.PRIORITY_CHOICES}:
            return Response({"detail": "Invalid notification priority."}, status=400)
        if action not in {choice[0] for choice in NotificationCampaign.ACTION_CHOICES}:
            return Response({"detail": "Invalid notification action."}, status=400)

        valid_until = None
        raw_valid_until = request.data.get("valid_until")
        if raw_valid_until:
            try:
                valid_until = timezone.datetime.fromisoformat(str(raw_valid_until))
                if timezone.is_naive(valid_until):
                    valid_until = timezone.make_aware(valid_until)
            except ValueError:
                return Response({"detail": "Invalid valid_until."}, status=400)

        campaign = NotificationCampaign.objects.create(
            title=title[:140],
            message=message[:1000],
            category=category,
            priority=priority,
            audience=audience,
            target_role=target_role if audience == "ROLE" else "",
            action=action,
            action_label=str(request.data.get("action_label") or "").strip()[:50],
            valid_until=valid_until,
            created_by=request.user,
        )

        if audience == "USERS":
            user_ids = request.data.get("user_ids") or []
            campaign.target_users.set(User.objects.filter(id__in=user_ids, is_active=True))
        delivered = materialize_campaign(campaign)
        return Response({
            "id": campaign.id,
            "delivered": delivered,
            "detail": "Notification campaign created.",
        }, status=201)


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
        target_user = None
        if audience == "TARGETED":
            target_user = User.objects.filter(
                pk=request.data.get("target_user_id"),
                role="CUSTOMER",
                is_active=True,
            ).first()
            if target_user is None:
                return Response({"detail": "Target customer user not found."}, status=400)
        elif audience != "ALL":
            return Response({"detail": "Offer audience must be ALL or TARGETED."}, status=400)

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

        # Mirror the offer into the generic notification inbox so customers see
        # the same promotion outside the Shop screen too.
        campaign = NotificationCampaign.objects.create(
            title=offer.title,
            message=offer.message,
            category="OFFER",
            priority="HIGH" if offer.priority >= 75 else "NORMAL",
            audience="USERS" if target_user else "CUSTOMERS",
            action=offer.action,
            action_label=offer.action_label,
            valid_until=offer.valid_until,
            created_by=request.user,
        )
        if target_user:
            campaign.target_users.add(target_user)
        delivered = materialize_campaign(campaign)

        return Response({
            "id": offer.id,
            "notification_campaign_id": campaign.id,
            "delivered": delivered,
            "detail": "Offer created and sent to eligible customer inboxes.",
        }, status=201)
