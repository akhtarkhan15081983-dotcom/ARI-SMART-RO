import re

from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import user_role
from assets.models import ROAsset
from customers.models import Customer

from .models import Job
from .ro_parts_ai import PART_CATALOG, analyze_ro_parts
from .ro_parts_models import (
    ROPartsInspection,
    ROPartsInspectionPhoto,
    ROPartsObservation,
)


MAX_PHOTO_BYTES = 10 * 1024 * 1024


def _employee_job(request, pk):
    return (
        Job.objects.select_related("customer", "ro_asset", "engineer", "engineer__user")
        .filter(pk=pk, engineer__user=request.user)
        .first()
    )


def _customer_for_user(user):
    customer = getattr(user, "customer_profile", None)
    if customer is not None:
        return customer
    phone = str(getattr(user, "phone", "") or "").strip()
    if not phone:
        return None
    return Customer.objects.filter(phone=phone, is_active=True).order_by("id").first()


def _normalise(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


PART_ALIASES = {
    "sediment_filter": ("sediment", "spun", "ppfilter", "ppfiltercartridge"),
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


def _catalog_key_for_name(name):
    value = _normalise(name)
    if not value:
        return None
    for key, aliases in PART_ALIASES.items():
        if any(_normalise(alias) in value for alias in aliases):
            return key
    return None


def _inventory_parts_for_job(job):
    result = {}
    usages = job.parts_used.select_related("inventory_item__part").all()
    for usage in usages:
        name = str(getattr(usage.inventory_item.part, "name", "") or "").strip()
        key = _catalog_key_for_name(name)
        if key:
            result[key] = {
                "part_key": key,
                "part_name": PART_CATALOG[key],
                "inventory_name": name,
                "used_at": usage.used_at,
            }
    return result


def _latest_confirmed_parts(asset, exclude_inspection_id=None):
    observations = ROPartsObservation.objects.filter(
        inspection__ro_asset=asset,
        inspection__status="CONFIRMED",
        confirmed=True,
    ).select_related("inspection")
    if exclude_inspection_id:
        observations = observations.exclude(inspection_id=exclude_inspection_id)
    observations = observations.order_by("part_key", "-inspection__confirmed_at", "-inspection__captured_at", "-id")
    latest = {}
    for observation in observations:
        latest.setdefault(observation.part_key, observation)
    return latest


def _date_label(observation):
    if not observation.installed_on:
        return "Date not available"
    date_text = observation.installed_on.strftime("%d-%b-%Y")
    if observation.date_source == "BASELINE_ASSUMED":
        return f"Baseline captured on {date_text}"
    if observation.date_source == "CARRIED_FORWARD":
        return f"Current since {date_text}"
    return f"Changed on {date_text}"


def _photo_payload(request, photo):
    try:
        url = photo.image.url
    except Exception:
        url = ""
    if url and request is not None:
        try:
            url = request.build_absolute_uri(url)
        except Exception:
            pass
    return {
        "id": photo.id,
        "url": url,
        "angle": photo.angle,
        "uploaded_at": photo.uploaded_at,
    }


def _observation_payload(observation):
    return {
        "part_key": observation.part_key,
        "part_name": observation.part_name,
        "confidence": float(observation.confidence or 0),
        "installed_on": observation.installed_on,
        "date_source": observation.date_source,
        "date_label": _date_label(observation),
        "evidence": observation.evidence_notes,
    }


def _asset_passport_payload(request, asset):
    latest = _latest_confirmed_parts(asset)
    latest_inspection = (
        ROPartsInspection.objects.filter(ro_asset=asset, status="CONFIRMED")
        .prefetch_related("photos")
        .order_by("-confirmed_at", "-captured_at", "-id")
        .first()
    )
    replacement_history = []
    history = (
        ROPartsObservation.objects.filter(
            inspection__ro_asset=asset,
            inspection__status="CONFIRMED",
            confirmed=True,
            date_source__in=["REPLACEMENT_CONFIRMED", "INVENTORY_JOB"],
        )
        .select_related("inspection", "inspection__engineer__user")
        .order_by("-installed_on", "-id")[:30]
    )
    for item in history:
        replacement_history.append(
            {
                **_observation_payload(item),
                "inspection_id": item.inspection_id,
                "confirmed_at": item.inspection.confirmed_at,
                "engineer": (
                    item.inspection.engineer.user.get_full_name()
                    if item.inspection.engineer_id
                    else ""
                ),
            }
        )
    return {
        "asset_id": asset.id,
        "asset_number": asset.asset_id,
        "serial_number": asset.serial_number,
        "ro_model": str(asset.ro_model),
        "status": asset.status,
        "last_visual_check": latest_inspection.confirmed_at if latest_inspection else None,
        "photos": (
            [_photo_payload(request, photo) for photo in latest_inspection.photos.all()]
            if latest_inspection
            else []
        ),
        "parts": [_observation_payload(latest[key]) for key in sorted(latest)],
        "replacement_history": replacement_history,
    }


class ROPartsScanAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        job = _employee_job(request, pk)
        if job is None:
            return Response({"detail": "Assigned job not found."}, status=status.HTTP_404_NOT_FOUND)
        if job.ro_asset_id is None:
            return Response(
                {"detail": "This job is not linked to an RO asset yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if job.status not in {"ARRIVED", "IN_PROGRESS"}:
            return Response(
                {"detail": "Capture RO parts only after arrival and while field work is active."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        photos = request.FILES.getlist("photos")
        if len(photos) < 3 or len(photos) > 4:
            return Response(
                {"detail": "Take 3 or 4 clear RO photos for a visual parts scan."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for photo in photos:
            if getattr(photo, "size", 0) > MAX_PHOTO_BYTES:
                return Response(
                    {"detail": "Each RO photo must be 10 MB or smaller."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            content_type = str(getattr(photo, "content_type", "") or "")
            if content_type and not content_type.startswith("image/"):
                return Response(
                    {"detail": "Only image files can be used for the RO visual scan."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        has_baseline = ROPartsObservation.objects.filter(
            inspection__ro_asset=job.ro_asset,
            inspection__status="CONFIRMED",
            confirmed=True,
        ).exists()
        inspection = ROPartsInspection.objects.create(
            ro_asset=job.ro_asset,
            customer=job.customer,
            job=job,
            engineer=job.engineer,
            inspection_type="VISUAL_CHECK" if has_baseline else "BASELINE",
            source="PHOTO_AI",
            status="CAPTURED",
            created_by=request.user,
        )
        angles = ["front", "inside_left", "inside_right", "overview"]
        stored_photos = []
        for index, image in enumerate(photos):
            stored_photos.append(
                ROPartsInspectionPhoto.objects.create(
                    inspection=inspection,
                    image=image,
                    angle=angles[index],
                )
            )

        ai_result = analyze_ro_parts(stored_photos)
        detected_by_key = {}
        for item in ai_result.get("detected_parts", []):
            key = str(item.get("part_key", "")).strip()
            if key not in PART_CATALOG:
                continue
            observation, _ = ROPartsObservation.objects.update_or_create(
                inspection=inspection,
                part_key=key,
                defaults={
                    "part_name": PART_CATALOG[key],
                    "confidence": item.get("confidence", 0) or 0,
                    "visible": True,
                    "confirmed": False,
                    "evidence_notes": str(item.get("evidence", ""))[:250],
                },
            )
            detected_by_key[key] = observation

        inventory_parts = _inventory_parts_for_job(job)
        for key, item in inventory_parts.items():
            observation, _ = ROPartsObservation.objects.update_or_create(
                inspection=inspection,
                part_key=key,
                defaults={
                    "part_name": PART_CATALOG[key],
                    "confidence": 1,
                    "visible": key in detected_by_key,
                    "confirmed": False,
                    "evidence_notes": f"Inventory job record: {item['inventory_name']}"[:250],
                },
            )
            detected_by_key[key] = observation

        inspection.ai_provider = ai_result.get("provider", "")
        inspection.ai_model = ai_result.get("model", "")
        inspection.ai_summary = ai_result.get("summary", "")
        inspection.raw_ai_result = ai_result
        inspection.status = "ANALYZED" if detected_by_key else "NEEDS_REVIEW"
        inspection.save(
            update_fields=[
                "ai_provider",
                "ai_model",
                "ai_summary",
                "raw_ai_result",
                "status",
            ]
        )

        previous = _latest_confirmed_parts(job.ro_asset, exclude_inspection_id=inspection.id)
        return Response(
            {
                "inspection_id": inspection.id,
                "inspection_type": inspection.inspection_type,
                "captured_at": inspection.captured_at,
                "ai_available": ai_result.get("available", False),
                "ai_summary": inspection.ai_summary,
                "detected_parts": [
                    {
                        "part_key": observation.part_key,
                        "part_name": observation.part_name,
                        "confidence": float(observation.confidence or 0),
                        "evidence": observation.evidence_notes,
                        "inventory_verified": observation.part_key in inventory_parts,
                        "selected": True,
                    }
                    for observation in inspection.observations.all()
                ],
                "existing_parts": [
                    _observation_payload(previous[key]) for key in sorted(previous)
                ],
                "catalog": [
                    {"part_key": key, "part_name": name}
                    for key, name in PART_CATALOG.items()
                ],
                "photos": [_photo_payload(request, photo) for photo in stored_photos],
                "date_policy": (
                    "First confirmed scan is a baseline because earlier replacement dates are unknown. "
                    "Future confirmed replacements use the actual service date."
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class ROPartsConfirmAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, inspection_id):
        job = _employee_job(request, pk)
        if job is None:
            return Response({"detail": "Assigned job not found."}, status=status.HTTP_404_NOT_FOUND)
        inspection = (
            ROPartsInspection.objects.select_related("ro_asset")
            .filter(pk=inspection_id, job=job, engineer=job.engineer)
            .first()
        )
        if inspection is None:
            return Response({"detail": "RO parts inspection not found."}, status=status.HTTP_404_NOT_FOUND)
        if inspection.status == "CONFIRMED":
            return Response(
                {
                    "message": "RO parts passport was already confirmed.",
                    "passport": _asset_passport_payload(request, inspection.ro_asset),
                }
            )

        submitted = request.data.get("parts", [])
        if not isinstance(submitted, list):
            return Response({"detail": "parts must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        requested = {}
        for item in submitted:
            if not isinstance(item, dict):
                continue
            key = str(item.get("part_key", "")).strip()
            if key not in PART_CATALOG:
                continue
            requested[key] = {
                "replaced": bool(item.get("replaced", False)),
                "evidence": str(item.get("evidence", ""))[:250],
            }

        inventory_parts = _inventory_parts_for_job(job)
        for key in inventory_parts:
            requested.setdefault(key, {"replaced": True, "evidence": ""})
            requested[key]["replaced"] = True

        if not requested:
            return Response(
                {"detail": "Confirm at least one RO part, or select a part manually from the catalog."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        previous = _latest_confirmed_parts(inspection.ro_asset, exclude_inspection_id=inspection.id)
        today = timezone.localdate()
        replacement_seen = False
        for key, decision in requested.items():
            current = inspection.observations.filter(part_key=key).first()
            prior = previous.get(key)
            replaced = decision["replaced"]
            if key in inventory_parts:
                installed_on = timezone.localtime(inventory_parts[key]["used_at"]).date()
                date_source = "INVENTORY_JOB"
                replaced = True
            elif replaced:
                installed_on = today
                date_source = "REPLACEMENT_CONFIRMED"
            elif prior and prior.installed_on:
                installed_on = prior.installed_on
                date_source = "CARRIED_FORWARD"
            else:
                installed_on = today
                date_source = "BASELINE_ASSUMED"

            replacement_seen = replacement_seen or replaced
            evidence = decision.get("evidence", "")
            if current and current.evidence_notes and not evidence:
                evidence = current.evidence_notes
            ROPartsObservation.objects.update_or_create(
                inspection=inspection,
                part_key=key,
                defaults={
                    "part_name": PART_CATALOG[key],
                    "confidence": current.confidence if current else 0,
                    "visible": current.visible if current else False,
                    "confirmed": True,
                    "installed_on": installed_on,
                    "date_source": date_source,
                    "evidence_notes": evidence[:250],
                },
            )

        inspection.status = "CONFIRMED"
        inspection.confirmed_at = timezone.now()
        if replacement_seen:
            inspection.inspection_type = "REPLACEMENT"
        inspection.save(update_fields=["status", "confirmed_at", "inspection_type"])

        return Response(
            {
                "message": "RO visual parts passport confirmed.",
                "passport": _asset_passport_payload(request, inspection.ro_asset),
            },
            status=status.HTTP_200_OK,
        )


class CustomerROPartsPassportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if user_role(request.user) != "CUSTOMER":
            return Response(
                {"detail": "This view is for the signed-in customer only."},
                status=status.HTTP_403_FORBIDDEN,
            )
        customer = _customer_for_user(request.user)
        if customer is None:
            return Response(
                {"customer_id": "", "assets": []},
                status=status.HTTP_200_OK,
            )
        assets = ROAsset.objects.filter(
            current_customer=customer,
            is_active=True,
        ).select_related("ro_model").order_by("asset_id")
        return Response(
            {
                "customer_id": customer.customer_id,
                "customer_name": customer.name,
                "assets": [_asset_passport_payload(request, asset) for asset in assets],
                "privacy": "Only RO assets currently linked to this signed-in customer are returned.",
            },
            status=status.HTTP_200_OK,
        )
