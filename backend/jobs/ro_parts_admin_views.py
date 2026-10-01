import json

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import user_role
from assets.models.asset import ROAlarm, ROAsset
from customers.models import Customer
from customers.rent_policy import rent_due_date
from products.models import ROModel
from tenancy.access import request_company

from .ro_parts_ai import PART_CATALOG
from .ro_parts_models import (
    ROPartsInspection,
    ROPartsInspectionPhoto,
    ROPartsObservation,
)
from .ro_parts_views import _asset_passport_payload


MAX_PHOTO_BYTES = 10 * 1024 * 1024


def _image_url(request, image_field):
    if not image_field:
        return ""
    try:
        return request.build_absolute_uri(image_field.url)
    except Exception:
        return ""


def _admin_company(request):
    if user_role(request.user) != "ADMIN":
        return None, Response(
            {"detail": "Only admin can manage all customer Digital RO passports."},
            status=status.HTTP_403_FORBIDDEN,
        )
    company = request_company(request)
    if company is None:
        return None, Response(
            {"detail": "Admin account is not linked to an active company."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return company, None


def _manual_setup_state(asset):
    confirmed = list(
        ROPartsInspection.objects.filter(ro_asset=asset, status="CONFIRMED")
        .order_by("confirmed_at", "captured_at", "id")[:2]
    )
    if not confirmed:
        return True, "Initial Digital RO baseline has not been captured yet."
    if (
        len(confirmed) == 1
        and confirmed[0].source == "MANUAL"
        and confirmed[0].inspection_type == "BASELINE"
        and confirmed[0].job_id is None
    ):
        return True, "Admin baseline can still be corrected before automatic history starts."
    return (
        False,
        "Verified service/inventory history has started. The baseline is locked to protect audit history.",
    )


def _parse_parts(raw):
    if raw in (None, ""):
        return []
    try:
        decoded = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError, json.JSONDecodeError):
        raise ValueError("Current parts must be a valid list.")
    if not isinstance(decoded, list):
        raise ValueError("Current parts must be a valid list.")

    result = []
    seen = set()
    for item in decoded:
        if isinstance(item, str):
            key = item.strip()
            installed_raw = ""
        elif isinstance(item, dict):
            key = str(item.get("part_key") or "").strip()
            installed_raw = str(item.get("installed_on") or "").strip()
        else:
            continue
        if key not in PART_CATALOG or key in seen:
            continue
        installed_on = None
        if installed_raw:
            installed_on = parse_date(installed_raw)
            if installed_on is None:
                raise ValueError(f"Invalid fitted date for {PART_CATALOG[key]}.")
        seen.add(key)
        result.append((key, installed_on))
    return result


def _validate_photos(request):
    photos = request.FILES.getlist("photos")
    if len(photos) > 4:
        raise ValueError("Upload up to 4 RO photos.")
    for photo in photos:
        if getattr(photo, "size", 0) > MAX_PHOTO_BYTES:
            raise ValueError("Each RO photo must be 10 MB or smaller.")
        content_type = str(getattr(photo, "content_type", "") or "")
        if content_type and not content_type.startswith("image/"):
            raise ValueError("Only image files can be used as RO photos.")
    return photos


class AdminROPartsPassportAPIView(APIView):
    """Tenant-scoped Digital RO register for company administrators."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        company, denied = _admin_company(request)
        if denied is not None:
            return denied

        query = str(request.GET.get("q") or "").strip()
        customers = Customer.objects.filter(company=company).order_by("name", "customer_id")
        if query:
            customers = customers.filter(
                Q(name__icontains=query)
                | Q(phone__icontains=query)
                | Q(customer_id__icontains=query)
                | Q(card_number__icontains=query)
                | Q(ro_model__icontains=query)
                | Q(ro_assets__asset_id__icontains=query)
                | Q(ro_assets__serial_number__icontains=query)
                | Q(ro_assets__ro_model__model_name__icontains=query)
            ).distinct()

        try:
            page = max(1, int(request.GET.get("page") or 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.GET.get("page_size") or 250)
        except (TypeError, ValueError):
            page_size = 250
        page_size = min(max(page_size, 1), 250)

        total_customer_count = customers.count()
        start = (page - 1) * page_size
        end = start + page_size

        rows = []
        total_active_alarms = 0
        for customer in customers[start:end]:
            assets = (
                ROAsset.objects.filter(current_customer=customer, is_active=True)
                .select_related("ro_model")
                .prefetch_related("ro_model__images")
                .order_by("asset_id")
            )
            asset_rows = []
            customer_alarm_count = 0
            for asset in assets:
                payload = _asset_passport_payload(request, asset)
                active_alarms = list(
                    ROAlarm.objects.filter(
                        ro_asset=asset,
                        status__in=["OPEN", "ACKNOWLEDGED"],
                    )
                    .order_by("-created_at")
                    .values(
                        "id",
                        "alarm_type",
                        "severity",
                        "status",
                        "title",
                        "message",
                        "due_date",
                        "observed_value",
                        "created_at",
                    )[:20]
                )
                setup_allowed, setup_message = _manual_setup_state(asset)
                payload["ro_model_id"] = asset.ro_model_id
                model_image = asset.ro_model.images.first()
                payload["ro_model_image_url"] = _image_url(
                    request,
                    model_image.image if model_image is not None else None,
                )
                payload["purchase_date"] = asset.purchase_date
                payload["next_filter_change_date"] = asset.next_filter_change_date
                payload["output_tds_attention_level"] = asset.output_tds_attention_level
                payload["alarm_monitoring_enabled"] = asset.alarm_monitoring_enabled
                payload["manual_setup_allowed"] = setup_allowed
                payload["manual_setup_message"] = setup_message
                payload["active_alarms"] = active_alarms
                payload["active_alarm_count"] = len(active_alarms)
                customer_alarm_count += len(active_alarms)
                asset_rows.append(payload)

            total_active_alarms += customer_alarm_count
            rows.append(
                {
                    "customer_id": customer.id,
                    "customer_number": customer.customer_id,
                    "card_number": customer.card_number,
                    "name": customer.name,
                    "phone": customer.phone,
                    "address": customer.address,
                    "area": customer.area,
                    "city": customer.city,
                    "master_ro_model": customer.ro_model,
                    "ownership_type": customer.ownership_type,
                    "installation_date": customer.installation_date,
                    "rent_due_day": customer.rent_due_day,
                    "current_rent_due_date": rent_due_date(
                        customer,
                        timezone.localdate().replace(day=1),
                    ),
                    "is_active": customer.is_active,
                    "active_alarm_count": customer_alarm_count,
                    "assets": asset_rows,
                }
            )

        return Response(
            {
                "company_id": company.id,
                "company_name": company.display_name,
                "query": query,
                "customer_count": total_customer_count,
                "returned_customer_count": len(rows),
                "page": page,
                "page_size": page_size,
                "has_more": end < total_customer_count,
                "next_page": page + 1 if end < total_customer_count else None,
                "active_alarm_count": total_active_alarms,
                "customers": rows,
            }
        )


    def patch(self, request):
        company, denied = _admin_company(request)
        if denied is not None:
            return denied

        try:
            customer_id = int(request.data.get("customer_id"))
            due_day = int(request.data.get("rent_due_day"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "Customer and rent due day are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if due_day < 1 or due_day > 31:
            return Response(
                {"detail": "Rent due day must be between 1 and 31."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer = get_object_or_404(
            Customer.objects.filter(company=company),
            pk=customer_id,
        )
        customer.rent_due_day = due_day
        customer.save(update_fields=["rent_due_day"])

        current_due = rent_due_date(
            customer,
            timezone.localdate().replace(day=1),
        )
        return Response(
            {
                "message": "RO rent due date updated.",
                "customer_id": customer.id,
                "rent_due_day": customer.rent_due_day,
                "current_rent_due_date": current_due,
            }
        )


class AdminROPartsBaselineAPIView(APIView):
    """Admin-only one-time/correctable Digital RO baseline before automatic history."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        company, denied = _admin_company(request)
        if denied is not None:
            return denied

        model_rows = []
        for model in (
            ROModel.objects.filter(is_active=True)
            .prefetch_related("images")
            .order_by("model_name", "id")
        ):
            first_image = model.images.first()
            model_rows.append(
                {
                    "id": model.id,
                    "model_name": model.model_name,
                    "capacity": model.capacity,
                    "business_type": model.business_type,
                    "available_for_sale": model.available_for_sale,
                    "available_for_rent": model.available_for_rent,
                    "image_url": _image_url(
                        request,
                        first_image.image if first_image is not None else None,
                    ),
                }
            )
        return Response(
            {
                "company_id": company.id,
                "models": model_rows,
                "parts": [
                    {"part_key": key, "part_name": name}
                    for key, name in PART_CATALOG.items()
                ],
                "policy": (
                    "Admin may create or correct the initial baseline until verified "
                    "service/inventory history starts. After that, history is locked "
                    "and future changes must come from normal service/inventory flows."
                ),
            }
        )

    def post(self, request):
        company, denied = _admin_company(request)
        if denied is not None:
            return denied

        try:
            customer_id = int(request.data.get("customer_id"))
            model_id = int(request.data.get("ro_model_id"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "Customer and RO model are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer = get_object_or_404(
            Customer.objects.filter(company=company),
            pk=customer_id,
        )
        ro_model = get_object_or_404(
            ROModel.objects.filter(is_active=True),
            pk=model_id,
        )

        ownership_type = str(
            request.data.get("ownership_type") or customer.ownership_type or "RENTAL"
        ).strip().upper()
        if ownership_type not in {"RENTAL", "PURCHASE"}:
            return Response(
                {"detail": "Ownership must be RENTAL or PURCHASE."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        date_raw = str(request.data.get("sale_installation_date") or "").strip()
        setup_date = parse_date(date_raw) if date_raw else None
        if date_raw and setup_date is None:
            return Response(
                {"detail": "Sale / installation date must be YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        filter_date_raw = str(
            request.data.get("next_filter_change_date") or ""
        ).strip()
        next_filter_change_date = (
            parse_date(filter_date_raw) if filter_date_raw else None
        )
        if filter_date_raw and next_filter_change_date is None:
            return Response(
                {"detail": "Next filter-change date must be YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        threshold_raw = str(
            request.data.get("output_tds_attention_level") or ""
        ).strip()
        output_tds_attention_level = None
        if threshold_raw:
            try:
                output_tds_attention_level = int(threshold_raw)
                if output_tds_attention_level < 0:
                    raise ValueError
            except (TypeError, ValueError):
                return Response(
                    {"detail": "TDS attention level must be a positive whole number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        monitoring_raw = str(
            request.data.get("alarm_monitoring_enabled", "true")
        ).strip().lower()
        alarm_monitoring_enabled = monitoring_raw not in {
            "0",
            "false",
            "no",
            "off",
        }

        try:
            parts = _parse_parts(request.data.get("parts"))
            photos = _validate_photos(request)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not parts:
            return Response(
                {"detail": "Select at least one current fitted RO part."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        asset_id_raw = request.data.get("asset_id")
        asset = None
        if asset_id_raw not in (None, ""):
            try:
                asset_id = int(asset_id_raw)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Invalid RO asset."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            asset = get_object_or_404(
                ROAsset.objects.filter(
                    current_customer=customer,
                    current_customer__company=company,
                    is_active=True,
                ),
                pk=asset_id,
            )
        else:
            existing_assets = list(
                ROAsset.objects.filter(
                    current_customer=customer,
                    is_active=True,
                ).order_by("id")[:2]
            )
            if len(existing_assets) == 1:
                asset = existing_assets[0]
            elif len(existing_assets) > 1:
                return Response(
                    {"detail": "Select which RO asset you want to initialise."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serial_number = str(request.data.get("serial_number") or "").strip()
        if not serial_number and asset is not None:
            serial_number = str(asset.serial_number or "").strip()
        if not serial_number:
            return Response(
                {"detail": "RO serial number is required for the initial Digital RO record."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conflict = ROAsset.objects.filter(serial_number__iexact=serial_number)
        if asset is not None:
            conflict = conflict.exclude(pk=asset.pk)
        if conflict.exists():
            return Response(
                {"detail": "This RO serial number is already linked to another asset."},
                status=status.HTTP_409_CONFLICT,
            )

        if asset is not None:
            setup_allowed, setup_message = _manual_setup_state(asset)
            if not setup_allowed:
                return Response(
                    {"detail": setup_message},
                    status=status.HTTP_409_CONFLICT,
                )

        with transaction.atomic():
            customer = Customer.objects.select_for_update().get(
                pk=customer.pk,
                company=company,
            )
            if asset is None:
                asset = ROAsset.objects.create(
                    ro_model=ro_model,
                    serial_number=serial_number,
                    status="INSTALLED",
                    current_customer=customer,
                    purchase_date=setup_date if ownership_type == "PURCHASE" else None,
                    next_filter_change_date=next_filter_change_date,
                    output_tds_attention_level=output_tds_attention_level,
                    alarm_monitoring_enabled=alarm_monitoring_enabled,
                )
                inspection = ROPartsInspection.objects.create(
                    ro_asset=asset,
                    customer=customer,
                    inspection_type="BASELINE",
                    source="MANUAL",
                    status="CONFIRMED",
                    confirmed_at=timezone.now(),
                    created_by=request.user,
                )
                created = True
            else:
                asset = ROAsset.objects.select_for_update().get(pk=asset.pk)
                asset.ro_model = ro_model
                asset.serial_number = serial_number
                asset.status = "INSTALLED"
                asset.current_customer = customer
                asset.purchase_date = (
                    setup_date if ownership_type == "PURCHASE" else None
                )
                asset.next_filter_change_date = next_filter_change_date
                asset.output_tds_attention_level = output_tds_attention_level
                asset.alarm_monitoring_enabled = alarm_monitoring_enabled
                asset.save(
                    update_fields=[
                        "ro_model",
                        "serial_number",
                        "status",
                        "current_customer",
                        "purchase_date",
                        "next_filter_change_date",
                        "output_tds_attention_level",
                        "alarm_monitoring_enabled",
                    ]
                )
                inspection = (
                    ROPartsInspection.objects.select_for_update()
                    .filter(
                        ro_asset=asset,
                        status="CONFIRMED",
                        source="MANUAL",
                        inspection_type="BASELINE",
                        job__isnull=True,
                    )
                    .order_by("id")
                    .first()
                )
                if inspection is None:
                    inspection = ROPartsInspection.objects.create(
                        ro_asset=asset,
                        customer=customer,
                        inspection_type="BASELINE",
                        source="MANUAL",
                        status="CONFIRMED",
                        confirmed_at=timezone.now(),
                        created_by=request.user,
                    )
                else:
                    inspection.customer = customer
                    inspection.confirmed_at = timezone.now()
                    inspection.created_by = request.user
                    inspection.save(
                        update_fields=["customer", "confirmed_at", "created_by"]
                    )
                    inspection.observations.all().delete()
                created = False

            customer.ro_model = ro_model.model_name
            customer.ownership_type = ownership_type
            if setup_date is not None:
                customer.installation_date = setup_date
            customer.save(
                update_fields=["ro_model", "ownership_type", "installation_date"]
            )

            for key, installed_on in parts:
                ROPartsObservation.objects.create(
                    inspection=inspection,
                    part_key=key,
                    part_name=PART_CATALOG[key],
                    confidence=1,
                    visible=True,
                    confirmed=True,
                    installed_on=installed_on,
                    date_source="BASELINE_ASSUMED",
                    evidence_notes="Admin-confirmed initial Digital RO baseline.",
                )

            if photos:
                for old_photo in inspection.photos.all():
                    try:
                        old_photo.image.delete(save=False)
                    except Exception:
                        pass
                    old_photo.delete()
                angles = ["admin_front", "admin_inside_left", "admin_inside_right", "admin_overview"]
                for index, image in enumerate(photos):
                    ROPartsInspectionPhoto.objects.create(
                        inspection=inspection,
                        image=image,
                        angle=angles[index],
                    )

        payload = _asset_passport_payload(request, asset)
        payload["ro_model_id"] = asset.ro_model_id
        first_image = asset.ro_model.images.first()
        payload["ro_model_image_url"] = _image_url(
            request,
            first_image.image if first_image is not None else None,
        )
        payload["purchase_date"] = asset.purchase_date
        payload["next_filter_change_date"] = asset.next_filter_change_date
        payload["output_tds_attention_level"] = asset.output_tds_attention_level
        payload["alarm_monitoring_enabled"] = asset.alarm_monitoring_enabled
        payload["manual_setup_allowed"] = True
        return Response(
            {
                "message": (
                    "Digital RO baseline saved. Future verified service and inventory "
                    "changes will continue the RO history automatically."
                ),
                "customer_id": customer.id,
                "asset": payload,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
