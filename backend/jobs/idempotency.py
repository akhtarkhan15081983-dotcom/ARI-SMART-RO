from dataclasses import dataclass
from typing import Any, Optional

from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response

from .models import ClientActionReceipt, Job


HEADER_NAME = "HTTP_X_ARI_ACTION_ID"
MAX_ACTION_ID_LENGTH = 160


@dataclass(frozen=True)
class IdempotencyReplay:
    action_id: str
    response: Optional[Response]


def action_id_from_request(request) -> str:
    raw = (request.META.get(HEADER_NAME) or "").strip()
    if not raw:
        return ""
    return raw[:MAX_ACTION_ID_LENGTH]


def replay_response(
    *,
    request,
    action_type: str,
    job: Optional[Job] = None,
) -> IdempotencyReplay:
    action_id = action_id_from_request(request)
    if not action_id:
        return IdempotencyReplay(action_id="", response=None)

    receipt = (
        ClientActionReceipt.objects.filter(
            user=request.user,
            action_id=action_id,
            action_type=action_type,
        )
        .select_related("job")
        .first()
    )
    if receipt is None:
        return IdempotencyReplay(action_id=action_id, response=None)

    if job is not None and receipt.job_id not in (None, job.id):
        return IdempotencyReplay(
            action_id=action_id,
            response=Response(
                {
                    "detail": "This action ID was already used for another job.",
                    "action_id": action_id,
                },
                status=409,
            ),
        )

    return IdempotencyReplay(
        action_id=action_id,
        response=Response(
            receipt.response_payload,
            status=receipt.response_status,
        ),
    )


def remember_response(
    *,
    request,
    action_id: str,
    action_type: str,
    response: Response,
    job: Optional[Job] = None,
) -> Response:
    if not action_id:
        return response

    payload: Any = response.data
    if isinstance(payload, dict):
        payload = dict(payload)
    elif isinstance(payload, list):
        payload = list(payload)
    else:
        payload = {"result": payload}

    payload.setdefault("action_id", action_id)
    payload.setdefault("idempotent_replay", False)
    response.data = payload

    with transaction.atomic():
        ClientActionReceipt.objects.get_or_create(
            user=request.user,
            action_id=action_id,
            defaults={
                "action_type": action_type,
                "job": job,
                "response_status": response.status_code,
                "response_payload": payload,
                "completed_at": timezone.now(),
            },
        )

    return response
