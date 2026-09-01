from django.urls import path

from .views import (
    UpdateLiveLocationAPIView,
    EngineerLiveMapAPIView,
    EmployeeProfileAPIView,
    EngineerListAPIView,
    AssignmentEmployeeListAPIView,
    FaceEnrollmentAPIView,
    AdminFaceEnrollmentControlAPIView,
    EmployeeManagementAPIView,
)
from .hrms import EmployeeHrmsDashboardAPIView, HolidayAPIView, HolidayDetailAPIView, LeaveRequestAPIView, LeaveReviewAPIView, PayrollActionAPIView, PayrollAPIView, PayrollExcelReportAPIView

urlpatterns = [
    path("employees/manage/", EmployeeManagementAPIView.as_view(), name="employee-management"),
    path("employees/hrms/dashboard/", EmployeeHrmsDashboardAPIView.as_view(), name="hrms-dashboard"),
    path("employees/hrms/holidays/", HolidayAPIView.as_view(), name="hrms-holidays"),
    path("employees/hrms/holidays/<int:holiday_id>/", HolidayDetailAPIView.as_view(), name="hrms-holiday-detail"),
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
