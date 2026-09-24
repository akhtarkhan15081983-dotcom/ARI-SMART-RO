from typing import Any

from .models import SystemAuditEvent


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def write_audit_event(
    *,
    request,
    action: str,
    entity_type: str,
    entity_id: Any = "",
    company=None,
    reason: str = "",
    before_state=None,
    after_state=None,
    metadata=None,
):
    user = getattr(request, "user", None)
    actor = user if getattr(user, "is_authenticated", False) else None
    company_id = getattr(company, "id", None) if company is not None else None
    company_name = getattr(company, "name", "") if company is not None else ""
    return SystemAuditEvent.objects.create(
        actor=actor,
        action=str(action)[:80],
        entity_type=str(entity_type)[:80],
        entity_id=str(entity_id or "")[:120],
        company_id=company_id,
        company_name=str(company_name or "")[:180],
        ip_address=_client_ip(request),
        device_id=str(request.headers.get("X-ARI-Device-ID", "") or "")[:128],
        reason=str(reason or "")[:500],
        before_state=before_state or {},
        after_state=after_state or {},
        metadata=metadata or {},
    )
