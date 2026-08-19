from django.urls import path

from .views import (
    CustomerListAPIView,
    MyCustomersAPIView,
    CustomerCreateAPIView,
    CustomerDetailAPIView,
    CustomerServiceHistoryAPIView,
    CustomerSearchAPIView,
    CustomerUpdateAPIView,
    WalkInCustomerAPIView,
    AssignCustomerAPIView,
    CustomerRentAPIView,
    RentManagementAPIView,
    RentPaymentCreateAPIView,
    RentPaymentHistoryAPIView,
    CustomerProfileAPIView,
    MyROAPIView,
)

urlpatterns = [
    path(
        "profile/",
        CustomerProfileAPIView.as_view(),
        name="customer-profile",
    ),

    path(
        "my-ro/",
        MyROAPIView.as_view(),
        name="my-ro",
    ),

    # ========================================================
    # ENGINEER CUSTOMERS
    # ========================================================

    path(
        "my-customers/",
        MyCustomersAPIView.as_view(),
        name="my-customers",
    ),

    # ========================================================
    # CUSTOMER LIST
    # ========================================================

    path(
        "",
        CustomerListAPIView.as_view(),
        name="customer-list",
    ),

    # ========================================================
    # CREATE CUSTOMER
    # ========================================================

    path(
        "create/",
        CustomerCreateAPIView.as_view(),
        name="customer-create",
    ),

    # ========================================================
    # CUSTOMER DETAIL
    # ========================================================

    path(
        "<int:pk>/",
        CustomerDetailAPIView.as_view(),
        name="customer-detail",
    ),

    # ========================================================
    # CUSTOMER SERVICE & PARTS HISTORY
    # ========================================================

    path(
        "<int:pk>/service-history/",
        CustomerServiceHistoryAPIView.as_view(),
        name="customer-service-history",
    ),

    # ========================================================
    # CUSTOMER SEARCH
    # ========================================================

    path(
        "search/",
        CustomerSearchAPIView.as_view(),
        name="customer-search",
    ),

    # ========================================================
    # CUSTOMER UPDATE
    # ========================================================

    path(
        "<int:pk>/update/",
        CustomerUpdateAPIView.as_view(),
        name="customer-update",
    ),

    # ========================================================
    # WALK-IN CUSTOMER
    # ========================================================

    path(
        "walk-in/",
        WalkInCustomerAPIView.as_view(),
        name="walk_in_customer",
    ),

    # ========================================================
    # ASSIGN ENGINEER
    # ========================================================

    path(
        "<int:pk>/assign/",
        AssignCustomerAPIView.as_view(),
        name="customer-assign",
    ),

    # ========================================================
    # CUSTOMER RENT & PAYMENT
    # ========================================================

    path(
        "rent/",
        CustomerRentAPIView.as_view(),
        name="customer-rent",
    ),

    # ========================================================
    # ADMIN / MANAGER / OFFICE
    # RENT MANAGEMENT
    # ========================================================

    path(
        "rent-management/",
        RentManagementAPIView.as_view(),
        name="rent-management",
    ),

    # ========================================================
    # OFFICE / ADMIN RENT PAYMENT
    # ========================================================

    path(
        "rent-management/payment/",
        RentPaymentCreateAPIView.as_view(),
        name="rent-management-payment",
    ),

    path(
        "rent-management/payments/",
        RentPaymentHistoryAPIView.as_view(),
        name="rent-management-payment-history",
    ),
]
