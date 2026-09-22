from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomerRegisterAPIView,
    SendOTPAPIView,
    VerifyOTPAPIView,
    LoginAPIView,
    ChangePasswordAPIView,
    ForgotPasswordRequestAPIView,
    AdminPasswordResetRequestListAPIView,
    AdminPasswordResetReviewAPIView,
    CompleteAdminApprovedPasswordResetAPIView,
    AdminSystemAuditAPIView,
)
from .sim_verification import SimVerificationPollAPIView, SimVerificationStartAPIView, SmsGatewayIngestAPIView
from .engagement import CustomerEngagementAPIView
from .notifications import (
    AdminNotificationCampaignAPIView,
    AdminOfferAPIView,
    NotificationCenterAPIView,
)


urlpatterns = [
    path("admin/system-audit/", AdminSystemAuditAPIView.as_view(), name="admin-system-audit"),
    path("notifications/", NotificationCenterAPIView.as_view(), name="notification-center"),
    path("admin/notification-campaigns/", AdminNotificationCampaignAPIView.as_view(), name="admin-notification-campaigns"),
    path("admin/offers/", AdminOfferAPIView.as_view(), name="admin-offers"),
    path("customer-engagement/", CustomerEngagementAPIView.as_view(), name="customer-engagement"),
    path("sim-verification/start/", SimVerificationStartAPIView.as_view(), name="sim-verification-start"),
    path("sim-verification/poll/", SimVerificationPollAPIView.as_view(), name="sim-verification-poll"),
    path("sms-gateway/ingest/", SmsGatewayIngestAPIView.as_view(), name="sms-gateway-ingest"),

    # ========================================================
    # CUSTOMER REGISTRATION
    # ========================================================

    path(
        "register/",
        CustomerRegisterAPIView.as_view(),
        name="customer-register",
    ),

    # ========================================================
    # SEND OTP
    # ========================================================

    path(
        "send-otp/",
        SendOTPAPIView.as_view(),
        name="send-otp",
    ),

    # ========================================================
    # VERIFY OTP
    # ========================================================

    path(
        "verify-otp/",
        VerifyOTPAPIView.as_view(),
        name="verify-otp",
    ),

    # ========================================================
    # LOGIN
    # ========================================================

    path(
        "login/",
        LoginAPIView.as_view(),
        name="login",
    ),

    # ========================================================
    # CHANGE PASSWORD
    # ========================================================

    path(
        "change-password/",
        ChangePasswordAPIView.as_view(),
        name="change-password",
    ),
    path(
        "forgot-password/request/",
        ForgotPasswordRequestAPIView.as_view(),
        name="forgot-password-request",
    ),
    path(
        "forgot-password/complete/",
        CompleteAdminApprovedPasswordResetAPIView.as_view(),
        name="forgot-password-complete",
    ),
    path(
        "admin/password-reset-requests/",
        AdminPasswordResetRequestListAPIView.as_view(),
        name="admin-password-reset-request-list",
    ),
    path(
        "admin/password-reset-requests/<int:reset_request_id>/review/",
        AdminPasswordResetReviewAPIView.as_view(),
        name="admin-password-reset-request-review",
    ),
    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),
]
