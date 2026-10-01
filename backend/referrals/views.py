import hashlib
import json
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from jobs.idempotency import action_id_from_request, replay_response, remember_response
from tenancy.access import has_feature_access, request_company

from .models import Referral, WalletReward, WalletLedgerEntry
from .serializers import (
    ClaimReferralSerializer,
    ReferralSerializer,
    WalletRewardSerializer,
    WalletLedgerEntrySerializer,
)
from .services import (
    get_or_create_profile,
    claim_referral,
    claim_welcome_reward,
    qualify_referral,
    calculate_max_redeemable,
    redeem_wallet,
    expire_rewards,
)



class ReferralFeaturePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if str(getattr(user, "role", "") or "").upper() == "CUSTOMER":
            return bool(getattr(user, "is_verified", False))
        return has_feature_access(request, "referral")


class ReferralMeAPIView(APIView):
    permission_classes = [IsAuthenticated, ReferralFeaturePermission]

    def get(self, request):
        expire_rewards()
        profile = get_or_create_profile(request.user)
        rewards = WalletReward.objects.filter(owner=request.user).order_by("activated_at", "id")
        referrals = Referral.objects.filter(referrer=request.user).select_related("referred_user")
        transactions = WalletLedgerEntry.objects.filter(user=request.user).select_related("reward")[:100]
        total = sum((r.remaining_amount for r in rewards if r.status in {"ACTIVE", "PARTIAL"}), Decimal("0.00"))
        points_value = sum((r.remaining_amount for r in rewards if r.reward_type == "APP_REFERRAL_POINTS" and r.status in {"ACTIVE", "PARTIAL"}), Decimal("0.00"))
        referral_stats = referrals.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status="PENDING")),
            qualified=Count("id", filter=Q(status="QUALIFIED")),
            under_review=Count("id", filter=Q(status="REVIEW")),
        )
        credited = WalletLedgerEntry.objects.filter(
            user=request.user,
            entry_type="CREDIT",
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        return Response({
            "success": True,
            "referral_code": profile.referral_code,
            "wallet_balance": total,
            "points_balance": int(points_value * 10),
            "lifetime_earnings": credited,
            "referral_stats": referral_stats,
            "capabilities": {
                "can_refer": True,
                "can_apply_referral_code": request.user.role == "CUSTOMER",
                "can_claim_welcome_reward": request.user.role == "CUSTOMER",
            },
            "program": {
                "app_referral_points": 100,
                "app_referral_value": "10.00",
                "cash_bill_wallet_percent": "30.00",
                "app_points_allowed_categories": ["PURCHASE", "PARTS", "SERVICE"],
                "rent_discount_monthly": "50.00",
                "rent_discount_months": 12,
                "minimum_rent_cash": "100.00",
            },
            "rewards": WalletRewardSerializer(rewards, many=True).data,
            "referrals": ReferralSerializer(referrals, many=True).data,
            "transactions": WalletLedgerEntrySerializer(transactions, many=True).data,
        })


class ClaimReferralAPIView(APIView):
    permission_classes = [IsAuthenticated, ReferralFeaturePermission]

    def post(self, request):
        serializer = ClaimReferralSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            referral = claim_referral(
                referred_user=request.user,
                code=serializer.validated_data["referral_code"],
                claim_fingerprint=request.headers.get("X-ARI-Device-ID", ""),
            )
        except Exception as exc:
            detail = getattr(exc, "detail", str(exc))
            return Response({"success": False, "message": detail}, status=400)
        message = (
            "Referral saved. It is under automatic security review."
            if referral.status == "REVIEW"
            else "Referral saved. Referrer received 100 points; rent benefit activates after successful installation."
        )
        return Response({"success": True, "message": message, "referral": ReferralSerializer(referral).data}, status=201)


class WelcomeRewardAPIView(APIView):
    permission_classes = [IsAuthenticated, ReferralFeaturePermission]

    def post(self, request):
        try:
            reward = claim_welcome_reward(request.user)
        except Exception as exc:
            detail = getattr(exc, "detail", str(exc))
            return Response({"success": False, "message": detail}, status=400)
        return Response({"success": True, "message": "₹50 ARI Welcome Reward activated.", "reward": WalletRewardSerializer(reward).data}, status=201)


class WalletBalanceAPIView(APIView):
    permission_classes = [IsAuthenticated, ReferralFeaturePermission]

    def get(self, request):
        expire_rewards()
        rewards = WalletReward.objects.filter(owner=request.user, status__in=["ACTIVE", "PARTIAL"], remaining_amount__gt=0)
        balance = sum((r.remaining_amount for r in rewards), Decimal("0.00"))
        return Response({"success": True, "wallet_balance": balance, "rewards": WalletRewardSerializer(rewards, many=True).data})


class WalletHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated, ReferralFeaturePermission]

    def get(self, request):
        entries = WalletLedgerEntry.objects.filter(user=request.user).select_related("reward")
        total_count = entries.count()
        return Response({
            "success": True,
            "count": total_count,
            "entries": WalletLedgerEntrySerializer(entries[:100], many=True).data,
        })


class WalletQuoteAPIView(APIView):
    permission_classes = [IsAuthenticated, ReferralFeaturePermission]

    def post(self, request):
        try:
            bill = Decimal(str(request.data.get("bill_amount"))).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError):
            return Response({"success": False, "message": "Invalid bill_amount."}, status=400)
        category = str(request.data.get("category", "")).upper().strip()
        if category not in {"RENT", "PURCHASE", "PARTS", "SERVICE"}:
            return Response({"success": False, "message": "Invalid category."}, status=400)
        max_use = calculate_max_redeemable(user=request.user, bill_amount=bill, category=category)
        return Response({"success": True, "bill_amount": bill, "category": category, "maximum_wallet_use": max_use, "customer_payable": bill - max_use})


class WalletRedeemAPIView(APIView):
    permission_classes = [IsAuthenticated, ReferralFeaturePermission]

    @transaction.atomic
    def post(self, request):
        try:
            bill = Decimal(str(request.data.get("bill_amount"))).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError):
            return Response({"success": False, "message": "Invalid bill_amount."}, status=400)
        category = str(request.data.get("category", "")).upper().strip()
        reference_type = str(request.data.get("reference_type", "")).strip()
        reference_id = str(request.data.get("reference_id", "")).strip()
        if category not in {"RENT", "PURCHASE", "PARTS", "SERVICE"} or not reference_type or not reference_id:
            return Response({"success": False, "message": "category, reference_type and reference_id are required."}, status=400)
        identity = json.dumps(
            [str(bill), category, reference_type, reference_id], separators=(",", ":"),
        )
        action_type = "wallet_redeem:" + hashlib.sha256(identity.encode()).hexdigest()[:16]
        action_id = action_id_from_request(request)
        if action_id:
            # Lock before receipt lookup so concurrent identical retries cannot
            # both debit the wallet before one receipt becomes visible.
            type(request.user).objects.select_for_update().get(pk=request.user.pk)
        replay = replay_response(request=request, action_type=action_type)
        if replay.response is not None:
            return replay.response
        try:
            result = redeem_wallet(
                user=request.user,
                bill_amount=bill,
                category=category,
                reference_type=reference_type,
                reference_id=reference_id,
            )
        except Exception as exc:
            detail = getattr(exc, "detail", str(exc))
            return Response({"success": False, "message": detail}, status=400)
        response = Response({"success": True, **result})
        if action_id:
            response.data = json.loads(json.dumps(response.data, cls=DjangoJSONEncoder))
        return remember_response(
            request=request, action_id=action_id,
            action_type=action_type, response=response,
        )


class QualifyReferralAPIView(APIView):
    permission_classes = [IsAuthenticated]
    ALLOWED_ROLES = {"ADMIN", "MANAGER", "OFFICE"}

    def post(self, request, pk):
        if request.user.role not in self.ALLOWED_ROLES:
            return Response({"success": False, "message": "Only Admin, Manager or Office can qualify referrals."}, status=403)
        company = request_company(request)
        if company is None:
            return Response(
                {"success": False, "message": "Active company workspace not found."},
                status=403,
            )
        referral = Referral.objects.filter(pk=pk).select_related(
            "referrer",
            "referred_user",
        ).first()
        if referral is None:
            return Response({"success": False, "message": "Referral not found."}, status=404)

        from customers.models import Customer

        def user_in_company(user):
            if user.company_memberships.filter(
                company=company,
                is_active=True,
            ).exists():
                return True
            return Customer.objects.filter(
                user=user,
                company=company,
            ).exists()

        if not user_in_company(referral.referrer) or not user_in_company(referral.referred_user):
            return Response(
                {"success": False, "message": "Referral does not belong to your company."},
                status=404,
            )

        referred_type = str(request.data.get("referred_type", "")).upper().strip()
        try:
            amount = Decimal(str(request.data.get("qualifying_amount", "0"))).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError):
            return Response({"success": False, "message": "Invalid qualifying_amount."}, status=400)
        try:
            referral = qualify_referral(pk, referred_type=referred_type, qualifying_amount=amount, actor=request.user)
        except Exception as exc:
            detail = getattr(exc, "detail", str(exc))
            return Response({"success": False, "message": detail}, status=400)
        return Response({"success": True, "referral": ReferralSerializer(referral).data, "rewards": WalletRewardSerializer(referral.rewards.all(), many=True).data})
