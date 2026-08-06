from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PartCategoryViewSet,
    PartMasterViewSet,
)

router = DefaultRouter()

router.register(
    "part-categories",
    PartCategoryViewSet,
    basename="part-category"
)

router.register(
    "parts",
    PartMasterViewSet,
    basename="part-master"
)

urlpatterns = [
    path("", include(router.urls)),
]