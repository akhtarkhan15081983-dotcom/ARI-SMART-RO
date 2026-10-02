from datetime import timedelta

from django.utils import timezone

from .hr_phase1 import EmployeeDocumentComplianceAPIView as Phase1DocumentComplianceAPIView


class EmployeeDocumentComplianceAPIView(Phase1DocumentComplianceAPIView):
    """Keep the legacy list contract while exposing richer Phase-1 statuses."""

    def get(self, request):
        response = super().get(request)
        if response.status_code != 200:
            return response
        today = timezone.localdate()
        for row in response.data.get("documents", []):
            expiry = row.get("expiry_date")
            if expiry is None:
                expiry_state = "NO_EXPIRY"
            elif expiry < today:
                expiry_state = "EXPIRED"
            elif expiry <= today + timedelta(days=30):
                expiry_state = "EXPIRING_SOON"
            else:
                expiry_state = "VALID"
            row["expiry_state"] = expiry_state
        return response
