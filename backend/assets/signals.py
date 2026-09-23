from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import ROAsset, ROAssetComponent, ROAssetComponentEvent


def _event(component, action, *, source_reference="", actor=None, remarks="", metadata=None):
    ROAssetComponentEvent.objects.create(
        asset=component.asset,
        component=component,
        action=action,
        part=component.part,
        quantity=component.quantity,
        serial_number=component.serial_number,
        from_status="",
        to_status=component.status,
        source_reference=source_reference,
        actor=actor,
        remarks=str(remarks or "")[:500],
        metadata=metadata or {},
    )


def ensure_factory_bom(asset):
    """Create the digital factory BOM once for a physical RO asset.

    Serialized parts are created as scan-pending placeholders. Non-serialized
    parts are immediately represented by quantity so every machine has a full
    digital parts list even where there is no QR/serial on the physical part.
    """
    standard_parts = asset.ro_model.standard_parts.select_related("part").all()
    for line in standard_parts:
        part = line.part
        existing = ROAssetComponent.objects.filter(
            asset=asset,
            part=part,
            source="FACTORY_BOM",
            source_reference=f"MODEL:{asset.ro_model_id}",
            status="ACTIVE",
        ).exists()
        if existing:
            continue
        component = ROAssetComponent.objects.create(
            asset=asset,
            part=part,
            quantity=line.quantity,
            source="FACTORY_BOM",
            source_reference=f"MODEL:{asset.ro_model_id}",
            scan_status="PENDING" if part.is_serialized else "NOT_REQUIRED",
            notes=line.remarks,
        )
        _event(
            component,
            "CREATED",
            source_reference=component.source_reference,
            remarks="Created from RO model standard BOM.",
            metadata={"mandatory": line.is_mandatory},
        )


def _sync_used_part(*, asset, part, inventory_item, quantity, source, source_reference, actor=None, remarks=""):
    if asset is None or part is None:
        return

    serial = ""
    if inventory_item is not None:
        serial = str(inventory_item.serial_number or "").strip()

    # A service/install record with the same part represents the new current
    # fitment. Preserve old rows as history instead of deleting them.
    previous = list(
        ROAssetComponent.objects.select_for_update().filter(
            asset=asset,
            part=part,
            status="ACTIVE",
        )
    )
    now = timezone.now()
    for old in previous:
        old.status = "REPLACED"
        old.removed_at = now
        old.save(update_fields=["status", "removed_at", "updated_at"])
        _event(
            old,
            "REPLACED",
            source_reference=source_reference,
            actor=actor,
            remarks=f"Superseded by {source.lower()} component record.",
        )

    component = ROAssetComponent.objects.create(
        asset=asset,
        part=part,
        inventory_item=inventory_item,
        quantity=max(int(quantity or 1), 1),
        serial_number=serial,
        source=source,
        source_reference=source_reference,
        status="ACTIVE",
        scan_status=(
            "VERIFIED"
            if part.is_serialized and serial
            else "PENDING"
            if part.is_serialized
            else "NOT_REQUIRED"
        ),
        installed_by=actor,
        notes=str(remarks or "")[:300],
    )
    _event(
        component,
        "SCAN_VERIFIED" if component.scan_status == "VERIFIED" else "CREATED",
        source_reference=source_reference,
        actor=actor,
        remarks=remarks,
    )


@receiver(post_save, sender=ROAsset)
def create_factory_passport(sender, instance, created, **kwargs):
    if created:
        ensure_factory_bom(instance)


@receiver(post_save, sender="installation.InstallationPart")
def sync_installation_component(sender, instance, created, **kwargs):
    if not created:
        return
    installation = instance.installation
    actor = getattr(getattr(installation, "engineer", None), "user", None)
    with transaction.atomic():
        _sync_used_part(
            asset=installation.ro_asset,
            part=instance.part,
            inventory_item=instance.inventory_item,
            quantity=instance.quantity,
            source="INSTALLATION",
            source_reference=f"INSTALLATION:{installation.installation_id}",
            actor=actor,
            remarks=f"Installation {installation.installation_id}",
        )


@receiver(post_save, sender="service.ServicePart")
def sync_service_component(sender, instance, created, **kwargs):
    if not created:
        return
    service = instance.service
    actor = getattr(getattr(service, "engineer", None), "user", None)
    with transaction.atomic():
        _sync_used_part(
            asset=service.ro_asset,
            part=instance.part,
            inventory_item=instance.inventory_item,
            quantity=instance.quantity,
            source="SERVICE",
            source_reference=f"SERVICE:{service.service_id}",
            actor=actor,
            remarks=instance.remarks or f"Service {service.service_id}",
        )
