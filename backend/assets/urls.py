from django.urls import path

from .views import (
    ROAssetListAPIView,
)

urlpatterns = [

    path(
        "",
        ROAssetListAPIView.as_view(),
        name="asset-list",
    ),

]