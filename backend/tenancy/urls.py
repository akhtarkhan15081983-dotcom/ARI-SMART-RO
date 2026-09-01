from django.urls import path

from .views import (
    CompanyCreateAPIView, MyCompaniesAPIView, PublicPlanListAPIView, PublicCompanyBrandAPIView,
    SuperAdminDashboardAPIView, SuperAdminSubscriptionStatusAPIView,
    SuperAdminCompanyOnboardingAPIView,
    SuperAdminCompanyLifecycleAPIView, SuperAdminCompanyLifecycleHistoryAPIView,
    SuperAdminCompanyDetailAPIView,
)

urlpatterns = [
    path("plans/", PublicPlanListAPIView.as_view(), name="saas-plan-list"),
    path("brand/<slug:slug>/", PublicCompanyBrandAPIView.as_view(), name="public-company-brand"),
    path("companies/", MyCompaniesAPIView.as_view(), name="my-companies"),
    path("companies/create/", CompanyCreateAPIView.as_view(), name="company-create"),
    path("super-admin/dashboard/", SuperAdminDashboardAPIView.as_view(), name="saas-super-admin-dashboard"),
    path("super-admin/companies/onboard/", SuperAdminCompanyOnboardingAPIView.as_view(), name="saas-super-admin-company-onboard"),
    path("super-admin/companies/<int:company_id>/subscription-status/", SuperAdminSubscriptionStatusAPIView.as_view(), name="saas-super-admin-subscription-status"),
    path("super-admin/companies/<int:company_id>/lifecycle/", SuperAdminCompanyLifecycleAPIView.as_view(), name="saas-super-admin-company-lifecycle"),
    path("super-admin/companies/<int:company_id>/lifecycle-history/", SuperAdminCompanyLifecycleHistoryAPIView.as_view(), name="saas-super-admin-company-lifecycle-history"),
    path("super-admin/companies/<int:company_id>/", SuperAdminCompanyDetailAPIView.as_view(), name="saas-super-admin-company-detail"),
]
