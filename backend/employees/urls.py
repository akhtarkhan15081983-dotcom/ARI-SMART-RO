from django.urls import path

from .views import (
    UpdateLiveLocationAPIView,
    EngineerLiveMapAPIView,
    EmployeeProfileAPIView,
    EngineerListAPIView,
    AssignmentEmployeeListAPIView,
    FaceEnrollmentAPIView,
    AdminFaceEnrollmentControlAPIView,
)
from .hrms import LeaveRequestAPIView, LeaveReviewAPIView, PayrollActionAPIView, PayrollAPIView, PayrollExcelReportAPIView

urlpatterns = [
    path("employees/hrms/leaves/", LeaveRequestAPIView.as_view(), name="hrms-leaves"),
    path("employees/hrms/leaves/<int:leave_id>/review/", LeaveReviewAPIView.as_view(), name="hrms-leave-review"),
    path("employees/hrms/payroll/", PayrollAPIView.as_view(), name="hrms-payroll"),
    path("employees/hrms/payroll/<int:payroll_id>/action/", PayrollActionAPIView.as_view(), name="hrms-payroll-action"),
    path("employees/hrms/reports/payroll.xlsx", PayrollExcelReportAPIView.as_view(), name="hrms-payroll-excel"),
    path(
        "employees/live-location/",
        UpdateLiveLocationAPIView.as_view(),
        name="live-location",
    ),
    path(
        "employees/live-map/",
        EngineerLiveMapAPIView.as_view(),
        name="live-map",
    ),
    path(
        "employees/profile/",
        EmployeeProfileAPIView.as_view(),
        name="employee-profile",
    ),
    path(
        "employees/face-enrollment/",
        FaceEnrollmentAPIView.as_view(),
        name="face-enrollment",
    ),
    path(
        "employees/<int:employee_id>/face-enrollment-control/",
        AdminFaceEnrollmentControlAPIView.as_view(),
        name="admin-face-enrollment-control",
    ),
    path(
        "employees/engineers/",
        EngineerListAPIView.as_view(),
        name="engineer-list",
    ),
    path(
        "employees/assignment-employees/",
        AssignmentEmployeeListAPIView.as_view(),
        name="assignment-employees",
    ),
]
