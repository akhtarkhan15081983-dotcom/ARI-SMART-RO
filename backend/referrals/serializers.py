from rest_framework import serializers
from .models import Referral, WalletReward, WalletLedgerEntry


class ClaimReferralSerializer(serializers.Serializer):
    referral_code = serializers.CharField(max_length=20)


class ReferralSerializer(serializers.ModelSerializer):
    referrer_name = serializers.CharField(source="referrer.get_full_name", read_only=True)
    referred_name = serializers.CharField(source="referred_user.get_full_name", read_only=True)

    class Meta:
        model = Referral
        fields = [
            "id", "referral_code", "referrer_name", "referred_name",
            "referred_type", "status", "qualifying_amount",
            "qualified_at", "risk_reasons", "created_at",
        ]
        read_only_fields = fields


class WalletRewardSerializer(serializers.ModelSerializer):
    reward_label = serializers.CharField(source="get_reward_type_display", read_only=True)

    class Meta:
        model = WalletReward
        fields = [
            "id", "reward_type", "reward_label", "total_amount",
            "used_amount", "remaining_amount", "max_bill_percent",
            "usage_categories", "status", "activated_at", "expires_at",
            "source_reference", "created_at",
        ]
        read_only_fields = fields


class WalletLedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletLedgerEntry
        fields = "__all__"
        read_only_fields = fields
