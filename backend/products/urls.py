from django.urls import path

from .views import (
    ProductCategoryAPIView,
    ROModelAPIView,
    ROModelPartAPIView,
    ProductSearchAPIView,
    CustomerShopCatalogAPIView,
    ROModelDetailAPIView,
    ROModelImageAPIView,
)


urlpatterns = [

    path(
        "categories/",
        ProductCategoryAPIView.as_view(),
        name="product-categories",
    ),

    path(
        "models/",
        ROModelAPIView.as_view(),
        name="ro-models",
    ),

    path(
        "models/<int:model_id>/",
        ROModelDetailAPIView.as_view(),
        name="ro-model-detail",
    ),

    path(
        "models/<int:model_id>/image/",
        ROModelImageAPIView.as_view(),
        name="ro-model-image",
    ),

    path(
        "parts/",
        ROModelPartAPIView.as_view(),
        name="ro-model-parts",
    ),

    path(
        "search/",
        ProductSearchAPIView.as_view(),
        name="product-search",
    ),

    path(
        "shop/catalog/",
        CustomerShopCatalogAPIView.as_view(),
        name="customer-shop-catalog",
    ),

]
