from django.urls import path

from .customer_alarm_refresh import ROAlarmAccessibleRefreshAPIView
from .views import (
    ROAlarmAssetListAPIView,
    ROAlarmAssetSettingsAPIView,
    ROAlarmListCreateAPIView,
    ROAlarmStatusAPIView,
    ROAssetListAPIView,
)

urlpatterns = [
    path(
        "",
        ROAssetListAPIView.as_view(),
        name="asset-list",
    ),
    path(
        "ro-alarm-assets/",
        ROAlarmAssetListAPIView.as_view(),
        name="ro-alarm-asset-list",
    ),
    path(
        "ro-alarm-assets/<int:pk>/settings/",
        ROAlarmAssetSettingsAPIView.as_view(),
        name="ro-alarm-asset-settings",
    ),
    path(
        "ro-alarms/",
        ROAlarmListCreateAPIView.as_view(),
        name="ro-alarm-list-create",
    ),
    path(
        "ro-alarms/refresh/",
        ROAlarmAccessibleRefreshAPIView.as_view(),
        name="ro-alarm-refresh",
    ),
    path(
        "ro-alarms/<int:pk>/status/",
        ROAlarmStatusAPIView.as_view(),
        name="ro-alarm-status",
    ),
]
