from django.urls import path
from .views import (
    ReferralMeAPIView,
    ClaimReferralAPIView,
    WelcomeRewardAPIView,
    WalletBalanceAPIView,
    WalletHistoryAPIView,
    WalletQuoteAPIView,
    WalletRedeemAPIView,
    QualifyReferralAPIView,
)

urlpatterns = [
    path("me/", ReferralMeAPIView.as_view(), name="referral-me"),
    path("claim/", ClaimReferralAPIView.as_view(), name="referral-claim"),
    path("welcome/claim/", WelcomeRewardAPIView.as_view(), name="welcome-reward"),
    path("wallet/", WalletBalanceAPIView.as_view(), name="wallet-balance"),
    path("wallet/history/", WalletHistoryAPIView.as_view(), name="wallet-history"),
    path("wallet/quote/", WalletQuoteAPIView.as_view(), name="wallet-quote"),
    path("wallet/redeem/", WalletRedeemAPIView.as_view(), name="wallet-redeem"),
    path("<int:pk>/qualify/", QualifyReferralAPIView.as_view(), name="referral-qualify"),
]
