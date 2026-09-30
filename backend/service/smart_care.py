from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from installation.models import InstallationPart

from .models import PartServiceCycleAudit, Service, ServiceIntervalPolicy, ServicePart


HEALTHY = "HEALTHY"
DUE_SOON = "SERVICE_DUE_SOON"
ACTION_REQUIRED = "ACTION_REQUIRED"
OVERDUE = "SERVICE_OVERDUE"
NOT_CONFIGURED = "NOT_CONFIGURED"

_STATUS_PRIORITY = {
    HEALTHY: 0,
    DUE_SOON: 1,
    ACTION_REQUIRED: 2,
    OVERDUE: 3,
}


def _policy_candidates(company, ro_asset, part, configuration_key=""):
    queryset = ServiceIntervalPolicy.objects.filter(
        company=company,
        part=part,
        is_active=True,
    ).filter(Q(ro_model=ro_asset.ro_model) | Q(ro_model__isnull=True))

    requested = (configuration_key or "").strip()
    allowed_keys = [""] if not requested else [requested, ""]
    policies = list(queryset.filter(configuration_key__in=allowed_keys))
    policies.sort(
        key=lambda policy: (
            1 if policy.ro_model_id == ro_asset.ro_model_id else 0,
            1 if requested and policy.configuration_key == requested else 0,
            policy.updated_at,
        ),
        reverse=True,
    )
    return policies


def resolve_interval_policy(company, ro_asset, part, configuration_key=""):
    candidates = _policy_candidates(company, ro_asset, part, configuration_key)
    return candidates[0] if candidates else None


def _latest_installation_part(ro_asset, part):
    return (
        InstallationPart.objects.filter(
            installation__ro_asset=ro_asset,
            installation__status="COMPLETED",
            part=part,
            installation__completed_date__isnull=False,
        )
        .select_related("installation", "part")
        .order_by("-installation__completed_date", "-id")
        .first()
    )


def _replacement_queryset(ro_asset, part):
    return (
        ServicePart.objects.filter(
            service__ro_asset=ro_asset,
            service__status="COMPLETED",
            service__completed_date__isnull=False,
            part=part,
            action=ServicePart.ACTION_REPLACED,
        )
        .select_related("service", "service__engineer", "part")
        .order_by("-service__completed_date", "-id")
    )


def cycle_start_for_part(ro_asset, part, before_service_part=None):
    replacements = _replacement_queryset(ro_asset, part)
    if before_service_part is not None:
        completed_at = before_service_part.service.completed_date
        if completed_at is not None:
            replacements = replacements.filter(
                Q(service__completed_date__lt=completed_at)
                | Q(service__completed_date=completed_at, id__lt=before_service_part.id)
            )
        else:
            replacements = replacements.exclude(pk=before_service_part.pk)

    replacement = replacements.first()
    if replacement is not None:
        return replacement.service.completed_date, "REPLACEMENT", replacement

    installed = _latest_installation_part(ro_asset, part)
    if installed is not None:
        return installed.installation.completed_date, "INSTALLATION", installed

    return None, None, None


def _due_date(started_at, interval_days):
    if started_at is None:
        return None
    start_date = started_at.date() if hasattr(started_at, "date") else started_at
    return start_date + timedelta(days=interval_days)


def reminder_schedule(policy, due_date):
    if policy is None or due_date is None:
        return []
    normalized = []
    for value in policy.reminder_days or []:
        try:
            days = int(value)
        except (TypeError, ValueError):
            continue
        if days < 0 or days in normalized:
            continue
        normalized.append(days)
    normalized.sort(reverse=True)
    return [
        {"days_before_due": days, "remind_on": due_date - timedelta(days=days)}
        for days in normalized
    ]


def part_health(company, ro_asset, part, configuration_key="", today=None):
    today = today or timezone.localdate()
    policy = resolve_interval_policy(company, ro_asset, part, configuration_key)
    started_at, source, _ = cycle_start_for_part(ro_asset, part)

    last_service = (
        Service.objects.filter(
            company=company,
            ro_asset=ro_asset,
            status="COMPLETED",
            completed_date__isnull=False,
        )
        .order_by("-completed_date", "-id")
        .first()
    )

    history = [
        {
            "service_id": item.service.service_id,
            "replaced_at": item.service.completed_date,
            "engineer_id": item.service.engineer_id,
            "verification_method": item.verification_method,
        }
        for item in _replacement_queryset(ro_asset, part)[:20]
    ]

    if policy is None:
        return {
            "part_id": part.id,
            "part_name": part.name,
            "installed_or_replaced_at": started_at,
            "cycle_source": source,
            "last_verified_service_date": last_service.completed_date if last_service else None,
            "expected_service_interval_days": None,
            "next_due_date": None,
            "days_remaining": None,
            "days_overdue": None,
            "health_status": NOT_CONFIGURED,
            "reminders": [],
            "verified_replacement_history": history,
        }

    due_date = _due_date(started_at, policy.interval_days)
    if due_date is None:
        status = ACTION_REQUIRED
        days_remaining = None
        days_overdue = None
    else:
        delta = (due_date - today).days
        if delta < 0:
            status = OVERDUE
            days_remaining = 0
            days_overdue = abs(delta)
        elif delta <= policy.due_soon_days:
            status = DUE_SOON
            days_remaining = delta
            days_overdue = 0
        else:
            status = HEALTHY
            days_remaining = delta
            days_overdue = 0

    return {
        "part_id": part.id,
        "part_name": part.name,
        "installed_or_replaced_at": started_at,
        "cycle_source": source,
        "last_verified_service_date": last_service.completed_date if last_service else None,
        "expected_service_interval_days": policy.interval_days,
        "next_due_date": due_date,
        "days_remaining": days_remaining,
        "days_overdue": days_overdue,
        "health_status": status,
        "reminders": reminder_schedule(policy, due_date),
        "verified_replacement_history": history,
    }


def asset_health(company, ro_asset, configuration_key="", today=None):
    installed_ids = InstallationPart.objects.filter(
        installation__ro_asset=ro_asset,
        installation__status="COMPLETED",
    ).values_list("part_id", flat=True)
    replacement_ids = ServicePart.objects.filter(
        service__ro_asset=ro_asset,
        service__status="COMPLETED",
        action=ServicePart.ACTION_REPLACED,
    ).values_list("part_id", flat=True)

    part_ids = set(installed_ids) | set(replacement_ids)
    from partmaster.models import PartMaster

    parts = PartMaster.objects.filter(id__in=part_ids, is_active=True).order_by("name")
    details = [
        part_health(company, ro_asset, part, configuration_key, today=today)
        for part in parts
    ]

    actionable = [item["health_status"] for item in details if item["health_status"] != NOT_CONFIGURED]
    if not actionable:
        overall = ACTION_REQUIRED if details else ACTION_REQUIRED
    else:
        overall = max(actionable, key=lambda value: _STATUS_PRIORITY.get(value, 0))

    return {
        "asset_id": ro_asset.asset_id,
        "ro_model": ro_asset.ro_model.model_name,
        "overall_status": overall,
        "parts": details,
    }


@transaction.atomic
def record_replacement_cycle(service_part):
    locked = (
        ServicePart.objects.select_for_update()
        .select_related(
            "service",
            "service__company",
            "service__customer",
            "service__ro_asset",
            "service__ro_asset__ro_model",
            "service__engineer",
            "part",
        )
        .get(pk=service_part.pk)
    )
    service = locked.service
    if locked.action != ServicePart.ACTION_REPLACED:
        return None
    if service.status != "COMPLETED" or service.completed_date is None:
        return None
    company = service.company or service.customer.company
    if company is None:
        return None

    existing = PartServiceCycleAudit.objects.filter(source_service_part=locked).first()
    if existing is not None:
        return existing

    policy = resolve_interval_policy(company, service.ro_asset, locked.part)
    previous_start, _, _ = cycle_start_for_part(
        service.ro_asset,
        locked.part,
        before_service_part=locked,
    )
    old_due = _due_date(previous_start, policy.interval_days) if policy else None
    new_due = _due_date(service.completed_date, policy.interval_days) if policy else None

    return PartServiceCycleAudit.objects.create(
        source_service_part=locked,
        company=company,
        ro_asset=service.ro_asset,
        part=locked.part,
        service=service,
        engineer=service.engineer,
        cycle_started_at=service.completed_date,
        old_due_date=old_due,
        new_due_date=new_due,
        verification_method=locked.verification_method,
    )


def record_completed_service_cycles(service):
    audits = []
    for service_part in service.parts_used.filter(action=ServicePart.ACTION_REPLACED):
        audit = record_replacement_cycle(service_part)
        if audit is not None:
            audits.append(audit)
    return audits
