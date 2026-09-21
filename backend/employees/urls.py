from django.urls import path

from .views import (
    UpdateLiveLocationAPIView,
    EngineerLiveMapAPIView,
    EmployeeProfileAPIView,
    EngineerListAPIView,
    AssignmentEmployeeListAPIView,
    FaceEnrollmentAPIView,
    AdminFaceEnrollmentControlAPIView,
    AdminFaceEnrollmentListAPIView,
    EmployeeManagementAPIView,
    EmployeeLifecycleAPIView,
    EmployeeCareerMovementAPIView,
    EmployeeCareerMovementActionAPIView,
    EmployeeIdCardAPIView,
    EmployeeIdVerifyAPIView,
)
from .hrms import EmployeeDocumentComplianceAPIView, EmployeeHrmsDashboardAPIView, EmployeePenaltyActionAPIView, EmployeePenaltyAPIView, HolidayAPIView, HolidayDetailAPIView, LeaveRequestAPIView, LeaveReviewAPIView, PayrollActionAPIView, PayrollAPIView, PayrollExcelReportAPIView, PerformanceReviewActionAPIView, PerformanceReviewAPIView
from .training import (
    TrainingDetailAPIView,
    TrainingLessonCompleteAPIView,
    TrainingListAPIView,
    TrainingQuizSubmitAPIView,
    TrainingTrainerReviewAPIView,
)

urlpatterns = [
    path("employees/manage/", EmployeeManagementAPIView.as_view(), name="employee-management"),
    path("employees/id-card/", EmployeeIdCardAPIView.as_view(), name="employee-id-card"),
    path("employees/verify-id/<str:code>/", EmployeeIdVerifyAPIView.as_view(), name="employee-id-verify"),
    path(
        "employees/manage/<int:employee_id>/lifecycle/",
        EmployeeLifecycleAPIView.as_view(),
        name="employee-lifecycle",
    ),
    path(
        "employees/manage/<int:employee_id>/career/",
        EmployeeCareerMovementAPIView.as_view(),
        name="employee-career-movements",
    ),
    path(
        "employees/manage/<int:employee_id>/career/<int:movement_id>/action/",
        EmployeeCareerMovementActionAPIView.as_view(),
        name="employee-career-movement-action",
    ),
    path("employees/hrms/dashboard/", EmployeeHrmsDashboardAPIView.as_view(), name="hrms-dashboard"),
    path("employees/hrms/holidays/", HolidayAPIView.as_view(), name="hrms-holidays"),
    path("employees/hrms/holidays/<int:holiday_id>/", HolidayDetailAPIView.as_view(), name="hrms-holiday-detail"),
    path("employees/hrms/leaves/", LeaveRequestAPIView.as_view(), name="hrms-leaves"),
    path("employees/hrms/leaves/<int:leave_id>/review/", LeaveReviewAPIView.as_view(), name="hrms-leave-review"),
    path("employees/hrms/payroll/", PayrollAPIView.as_view(), name="hrms-payroll"),
    path("employees/hrms/payroll/<int:payroll_id>/action/", PayrollActionAPIView.as_view(), name="hrms-payroll-action"),
    path("employees/hrms/penalties/", EmployeePenaltyAPIView.as_view(), name="hrms-penalties"),
    path("employees/hrms/penalties/<int:penalty_id>/action/", EmployeePenaltyActionAPIView.as_view(), name="hrms-penalty-action"),
    path("employees/hrms/performance/", PerformanceReviewAPIView.as_view(), name="hrms-performance"),
    path("employees/hrms/performance/<int:review_id>/action/", PerformanceReviewActionAPIView.as_view(), name="hrms-performance-action"),
    path("employees/hrms/documents/", EmployeeDocumentComplianceAPIView.as_view(), name="hrms-documents"),
    path("employees/hrms/training/", TrainingListAPIView.as_view(), name="hrms-training"),
    path("employees/hrms/training/<int:assignment_id>/", TrainingDetailAPIView.as_view(), name="hrms-training-detail"),
    path("employees/hrms/training/<int:assignment_id>/lessons/<int:lesson_id>/complete/", TrainingLessonCompleteAPIView.as_view(), name="hrms-training-lesson-complete"),
    path("employees/hrms/training/<int:assignment_id>/quiz/", TrainingQuizSubmitAPIView.as_view(), name="hrms-training-quiz"),
    path("employees/hrms/training/<int:assignment_id>/lessons/<int:lesson_id>/trainer-review/", TrainingTrainerReviewAPIView.as_view(), name="hrms-training-trainer-review"),
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
        "employees/admin/face-enrollments/",
        AdminFaceEnrollmentListAPIView.as_view(),
        name="admin-face-enrollment-list",
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
