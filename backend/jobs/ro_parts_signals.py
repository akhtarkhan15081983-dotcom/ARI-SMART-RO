from django.db.models.signals import post_save
from django.dispatch import receiver

from assets.models import ROAsset
from products.models import ProductCategory, ROModel

from .models import Job


PASSPORT_JOB_TYPES = {"SERVICE", "COMPLAINT", "INSTALLATION"}


def ensure_job_ro_asset(job):
    """Attach an RO asset to legacy/imported customer jobs when possible.

    Older imported customers can predate ROAsset records. For those customers,
    reuse an existing linked asset first; otherwise create a private inactive
    catalog model solely to anchor that customer's physical RO history.
    """
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
