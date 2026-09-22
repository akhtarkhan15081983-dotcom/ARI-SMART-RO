from django.urls import path

from .views import ClientErrorEventAPIView, ReportsExportAPIView, ReportsSummaryAPIView


urlpatterns = [
    path("client-errors/", ClientErrorEventAPIView.as_view(), name="client-errors"),
    path("summary/", ReportsSummaryAPIView.as_view(), name="reports-summary"),
    path("export/", ReportsExportAPIView.as_view(), name="reports-export"),
]
