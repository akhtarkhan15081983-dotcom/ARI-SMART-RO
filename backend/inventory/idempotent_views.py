from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from jobs.idempotency import action_id_from_request
from jobs.models import ClientActionReceipt

from .security_views import TenantScopedMyPartRequestsAPIView


class IdempotentTenantScopedMyPartRequestsAPIView(TenantScopedMyPartRequestsAPIView):
    """Prevent duplicate part requests when a client retries a lost response."""

    action_type = "PART_REQUEST_CREATE"

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        action_id = action_id_from_request(request)
        receipt = None
        created = False

        if action_id:
            receipt, created = ClientActionReceipt.objects.get_or_create(
                user=request.user,
                action_id=action_id,
                defaults={
                    "action_type": self.action_type,
                    "response_status": status.HTTP_202_ACCEPTED,
                    "response_payload": {"detail": "Part request action is processing."},
                },
            )
            if not created:
                if receipt.action_type != self.action_type:
                    return Response(
                        {
                            "detail": "This action ID was already used for another action type.",
                            "action_id": action_id,
                        },
                        status=status.HTTP_409_CONFLICT,
                    )
                if receipt.completed_at is None:
                    return Response(
                        {"detail": "This part request action is already processing.", "action_id": action_id},
                        status=status.HTTP_409_CONFLICT,
                    )
                payload = dict(receipt.response_payload or {})
                payload["action_id"] = action_id
                payload["idempotent_replay"] = True
                return Response(payload, status=receipt.response_status)

        response = super().create(request, *args, **kwargs)

        if action_id and receipt is not None:
            if 200 <= response.status_code < 300:
                payload = dict(response.data) if isinstance(response.data, dict) else {"result": response.data}
                payload["action_id"] = action_id
                payload["idempotent_replay"] = False
                response.data = payload
                receipt.response_status = response.status_code
                receipt.response_payload = payload
                receipt.completed_at = timezone.now()
                receipt.save(update_fields=["response_status", "response_payload", "completed_at"])
            elif created:
                receipt.delete()

        return response
