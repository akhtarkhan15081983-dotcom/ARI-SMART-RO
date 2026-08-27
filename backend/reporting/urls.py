from django.urls import path

from .views import ReportsExportAPIView, ReportsSummaryAPIView


urlpatterns = [
    path("summary/", ReportsSummaryAPIView.as_view(), name="reports-summary"),
    path("export/", ReportsExportAPIView.as_view(), name="reports-export"),
]
