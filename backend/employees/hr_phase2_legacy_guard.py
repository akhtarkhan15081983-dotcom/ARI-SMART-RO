from rest_framework import status
from rest_framework.response import Response

from .hr_phase1 import EmployeeHrLifecycleActionAPIView as Phase1EmployeeHrLifecycleActionAPIView


class EmployeeHrLifecycleActionAPIView(Phase1EmployeeHrLifecycleActionAPIView):
    """Compatibility endpoint guard for lifecycle transitions superseded by Phase-2.

    The Phase-1 endpoint remains available for onboarding review/readiness controls,
    but sensitive employment-state transitions must use the auditable Phase-2
    lifecycle/exit workflows so manager review, HR review, final approval,
    clearance and settlement gates cannot be bypassed.
    """

    PHASE2_ONLY_ACTIONS = {
        "EXTEND_PROBATION",
        "CONFIRM",
        "START_NOTICE",
        "SEPARATE",
    }

    def post(self, request, employee_id):
        action = str(request.data.get("action") or "").strip().upper()
        if action in self.PHASE2_ONLY_ACTIONS:
            return Response(
                {
                    "detail": (
                        "This lifecycle transition is controlled by Corporate HRMS "
                        "Phase-2. Use the Employee Lifecycle workflow so review, "
                        "approval, clearance and audit gates are enforced."
                    ),
                    "code": "PHASE2_LIFECYCLE_REQUIRED",
                    "action": action,
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().post(request, employee_id)
