from accounts.permissions import IsVerifiedCustomerOrOperations

from .views import ROAlarmRefreshAPIView


class ROAlarmAccessibleRefreshAPIView(ROAlarmRefreshAPIView):
    """Allow a verified customer to sync only their own scoped RO alarms."""

    permission_classes = [IsVerifiedCustomerOrOperations]
