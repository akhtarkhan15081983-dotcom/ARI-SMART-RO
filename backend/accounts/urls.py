from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomerRegisterAPIView,
    SendOTPAPIView,
    VerifyOTPAPIView,
    LoginAPIView,
    ChangePasswordAPIView,
)


urlpatterns = [

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
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),
]