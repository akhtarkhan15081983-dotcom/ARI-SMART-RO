from django.urls import path
from .views import (
    EngineerBagIssueAPIView,
    OCRVerifyAPIView,
    MyBagAPIView,
)

urlpatterns = [

    path(
        "inventory/issue/",
        EngineerBagIssueAPIView.as_view(),
        name="inventory-issue",
    ),

    path(
        "inventory/verify/",
        OCRVerifyAPIView.as_view(),
        name="inventory-verify",
    ),

    path(
        "inventory/my-bag/",
        MyBagAPIView.as_view(),
        name="my-bag",
    ),

]