from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

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


class ReferralMeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "CUSTOMER":
            return Response({"success": False, "message": "Only customers can access referral wallet."}, status=403)
        profile = get_or_create_profile(request.user)
        rewards = WalletReward.objects.filter(owner=request.user).order_by("activated_at", "id")
        referrals = Referral.objects.filter(referrer=request.user).select_related("referred_user")
        total = sum((r.remaining_amount for r in rewards if r.status in {"ACTIVE", "PARTIAL"}), Decimal("0.00"))
        return Response({
            "success": True,
            "referral_code": profile.referral_code,
            "wallet_balance": total,
            "rewards": WalletRewardSerializer(rewards, many=True).data,
            "referrals": ReferralSerializer(referrals, many=True).data,
        })


class ClaimReferralAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ClaimReferralSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            referral = claim_referral(
                referred_user=request.user,
                code=serializer.validated_data["referral_code"],
            )
        except Exception as exc:
            detail = getattr(exc, "detail", str(exc))
            return Response({"success": False, "message": detail}, status=400)
        return Response({"success": True, "message": "Referral attribution saved. Reward will activate after qualifying action.", "referral": ReferralSerializer(referral).data}, status=201)


class WelcomeRewardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            reward = claim_welcome_reward(request.user)
        except Exception as exc:
            detail = getattr(exc, "detail", str(exc))
            return Response({"success": False, "message": detail}, status=400)
        return Response({"success": True, "message": "₹50 ARI Welcome Reward activated.", "reward": WalletRewardSerializer(reward).data}, status=201)


class WalletBalanceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        expire_rewards()
        rewards = WalletReward.objects.filter(owner=request.user, status__in=["ACTIVE", "PARTIAL"], remaining_amount__gt=0)
        balance = sum((r.remaining_amount for r in rewards), Decimal("0.00"))
        return Response({"success": True, "wallet_balance": balance, "rewards": WalletRewardSerializer(rewards, many=True).data})


class WalletHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        entries = WalletLedgerEntry.objects.filter(user=request.user).select_related("reward")
        return Response({"success": True, "count": entries.count(), "entries": WalletLedgerEntrySerializer(entries, many=True).data})


class WalletQuoteAPIView(APIView):
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

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
        return Response({"success": True, **result})


class QualifyReferralAPIView(APIView):
    permission_classes = [IsAuthenticated]
    ALLOWED_ROLES = {"ADMIN", "MANAGER", "OFFICE"}

    def post(self, request, pk):
        if request.user.role not in self.ALLOWED_ROLES:
            return Response({"success": False, "message": "Only Admin, Manager or Office can qualify referrals."}, status=403)
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
