from rest_framework import status
from rest_framework.response import Response

from .hr_phase1 import (
    EmployeeHrLifecycleActionAPIView as Phase1EmployeeHrLifecycleActionAPIView,
    _can_manage_lifecycle,
)


class EmployeeHrLifecycleActionAPIView(Phase1EmployeeHrLifecycleActionAPIView):
    """Keep Phase-1 onboarding controls, but force sensitive state changes to Phase-2.

    The compatibility endpoint is still used by the joining/onboarding workflow for
    manager review, HR review and Ready-for-Duty overrides. Employment-state
    transitions must use the auditable Phase-2 lifecycle/exit workflow so review,
    independent approval, clearance and settlement gates cannot be bypassed.
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
            # Preserve the existing 403 authorization contract for callers that
            # were never allowed to manage lifecycle state in the first place.
            if not _can_manage_lifecycle(request):
                return super().post(request, employee_id)
            return Response(
                {
                    "detail": (
                        "This employment-state transition is controlled by Corporate HRMS "
                        "Phase-2. Use the Employee Lifecycle workflow so review, approval, "
                        "clearance and audit gates are enforced."
                    ),
                    "code": "PHASE2_LIFECYCLE_REQUIRED",
                    "action": action,
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().post(request, employee_id)
