import re

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from assets.models import ROAsset
from products.models import ProductCategory, ROModel

from .models import Job, JobPartUsed
from .ro_parts_ai import PART_CATALOG
from .ro_parts_models import ROPartsInspection, ROPartsObservation


PASSPORT_JOB_TYPES = {"SERVICE", "COMPLAINT", "INSTALLATION"}

PART_ALIASES = {
    "sediment_filter": ("sediment", "spun", "ppfilter"),
    "pre_carbon": ("precarbon", "gac", "carbonblock", "carbonfilter"),
    "ro_membrane": ("romembrane", "membrane"),
    "post_carbon": ("postcarbon", "tasteodor", "t33"),
    "alkaline_filter": ("alkaline",),
    "copper_filter": ("copper",),
    "uv_chamber": ("uvchamber", "uvlamp", "uv"),
    "uf_filter": ("ufmembrane", "uffilter", "uf"),
    "mineral_cartridge": ("mineral",),
    "booster_pump": ("boosterpump", "pump"),
    "smps": ("smps", "powersupply", "adapter"),
    "solenoid_valve": ("solenoidvalve", "svvalve", "sv"),
    "flow_restrictor": ("flowrestrictor", "fr"),
    "tds_controller": ("tdscontroller", "tdscontrol"),
    "auto_flush_valve": ("autoflush", "flushvalve"),
    "low_pressure_switch": ("lowpressureswitch", "lps"),
    "high_pressure_switch": ("highpressureswitch", "hps"),
    "storage_tank": ("storagetank", "pressuretank", "tank"),
    "filter_housing": ("filterhousing", "prefilterhousing"),
    "membrane_housing": ("membranehousing",),
}


def _normalise(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _catalog_key_for_name(name):
    value = _normalise(name)
    if not value:
        return None
    for key, aliases in PART_ALIASES.items():
        if any(_normalise(alias) in value for alias in aliases):
            return key
    return None


def ensure_job_ro_asset(job):
    """Attach an RO asset to legacy/imported customer jobs when possible."""
    if job.ro_asset_id or job.job_type not in PASSPORT_JOB_TYPES or not job.customer_id:
        return job.ro_asset

    existing = (
        ROAsset.objects.filter(current_customer_id=job.customer_id, is_active=True)
        .order_by("id")
        .first()
    )
    if existing is not None:
        Job.objects.filter(pk=job.pk, ro_asset__isnull=True).update(ro_asset=existing)
        job.ro_asset = existing
        return existing

    legacy_name = str(job.customer.ro_model or "").strip() or "Legacy Customer RO"
    ro_model = ROModel.objects.filter(model_name__iexact=legacy_name).order_by("id").first()
    if ro_model is None:
        category, _ = ProductCategory.objects.get_or_create(
            name="Imported Customer RO Records",
            defaults={
                "description": "Private inactive models used to link legacy customer RO history.",
                "is_active": False,
            },
        )
        ro_model, _ = ROModel.objects.get_or_create(
            category=category,
            model_name=legacy_name,
            defaults={
                "capacity": "Unknown",
                "business_type": "RENT",
                "available_for_sale": False,
                "available_for_rent": False,
                "monthly_rent": 0,
                "installation_charge": 0,
                "security_deposit": 0,
                "selling_price": 0,
                "mrp": 0,
                "stock_quantity": 0,
                "description": "Legacy customer RO record created for visual service history.",
                "warranty_months": 0,
                "is_active": False,
            },
        )

    serial = f"LEGACY-{job.customer.customer_id or job.customer_id}-{job.customer_id}"
    asset, _ = ROAsset.objects.get_or_create(
        serial_number=serial,
        defaults={
            "ro_model": ro_model,
            "status": "INSTALLED",
            "current_customer": job.customer,
            "purchase_date": job.customer.installation_date,
            "is_active": True,
        },
    )
    if asset.current_customer_id != job.customer_id:
        asset.current_customer = job.customer
        asset.status = "INSTALLED"
        asset.is_active = True
        asset.save(update_fields=["current_customer", "status", "is_active"])

    Job.objects.filter(pk=job.pk, ro_asset__isnull=True).update(ro_asset=asset)
    job.ro_asset = asset
    return asset


@receiver(post_save, sender=Job)
def auto_link_legacy_ro_asset(sender, instance, **kwargs):
    ensure_job_ro_asset(instance)


@receiver(post_save, sender=JobPartUsed)
def sync_inventory_replacement_to_passport(sender, instance, created, **kwargs):
    """Upgrade a confirmed visual record when a serialized inventory part is installed.

    This makes the replacement date trustworthy regardless of whether the
    engineer captured RO photos before or after scanning the used-part QR.
    """
    if not created:
        return
    job = instance.job
    if not job.ro_asset_id:
        ensure_job_ro_asset(job)
    if not job.ro_asset_id:
        return

    part_name = str(getattr(instance.inventory_item.part, "name", "") or "").strip()
    key = _catalog_key_for_name(part_name)
    if key not in PART_CATALOG:
        return

    inspection = (
        ROPartsInspection.objects.filter(
            job=job,
            ro_asset_id=job.ro_asset_id,
            status="CONFIRMED",
        )
        .order_by("-confirmed_at", "-captured_at", "-id")
        .first()
    )
    if inspection is None:
        return

    current = inspection.observations.filter(part_key=key).first()
    used_at = instance.used_at or timezone.now()
    installed_on = timezone.localtime(used_at).date()
    ROPartsObservation.objects.update_or_create(
        inspection=inspection,
        part_key=key,
        defaults={
            "part_name": PART_CATALOG[key],
            "confidence": current.confidence if current else 1,
            "visible": current.visible if current else False,
            "confirmed": True,
            "installed_on": installed_on,
            "date_source": "INVENTORY_JOB",
            "evidence_notes": f"Inventory job record: {part_name}"[:250],
        },
    )
    if inspection.inspection_type != "REPLACEMENT":
        inspection.inspection_type = "REPLACEMENT"
        inspection.save(update_fields=["inspection_type"])
