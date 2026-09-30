from datetime import timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import (
    IsOperationsUser,
    IsStaffOperator,
    IsVerifiedCustomerOrOperations,
    user_role,
)
from accounts.system_notifications import upsert_notification
from tenancy.access import request_company
from tenancy.models import CompanyMembership

from .models.asset import ROAlarm, ROAsset
from .serializers import (
    ROAlarmAssetSerializer,
    ROAlarmSerializer,
    ROAssetSerializer,
)


MANUAL_ALARM_TYPES = {"LEAKAGE", "NOISE", "TASTE", "TDS", "LOW_FLOW", "OTHER"}
ALARM_TITLE = {
    "SERVICE_DUE": "RO service due",
    "FILTER_DUE": "RO filter change due",
    "LEAKAGE": "RO leakage reported",
    "NOISE": "Unusual RO noise reported",
    "TASTE": "Water taste change reported",
    "TDS": "TDS reading needs attention",
    "LOW_FLOW": "Low RO water flow reported",
    "OTHER": "RO attention requested",
}


def _scoped_assets(request):
    queryset = ROAsset.objects.filter(is_active=True).select_related(
        "ro_model",
        "current_customer",
        "current_customer__company",
        "current_customer__user",
    )
    role = user_role(request.user)
    if role == "CUSTOMER":
        customer = getattr(request.user, "customer_profile", None)
        if customer is None:
            return queryset.none()
        return queryset.filter(current_customer=customer)

    company = request_company(request)
    if company is None:
        return queryset.none()
    return queryset.filter(current_customer__company=company)


def _scoped_alarms(request):
    return ROAlarm.objects.filter(
        ro_asset__in=_scoped_assets(request),
    ).select_related(
        "ro_asset",
        "ro_asset__ro_model",
        "ro_asset__current_customer",
        "ro_asset__current_customer__company",
    )


def _alarm_recipients(alarm):
    recipients = {}
    customer = alarm.ro_asset.current_customer
    if customer is None:
        return []

    if customer.user_id and customer.user and customer.user.is_active:
        recipients[customer.user_id] = customer.user

    if customer.company_id:
        memberships = CompanyMembership.objects.filter(
            company_id=customer.company_id,
            is_active=True,
            user__is_active=True,
            user__role__in=["ADMIN", "MANAGER", "OFFICE"],
        ).select_related("user")
        for membership in memberships:
            recipients[membership.user_id] = membership.user

    return list(recipients.values())


def _notify_alarm(alarm, event):
    if event == "resolved":
        title = f"Resolved • {alarm.title}"
        message = (
            f"{alarm.ro_asset.asset_id}: {alarm.title} has been marked resolved."
        )
        priority = "NORMAL"
    elif event == "acknowledged":
        title = f"Acknowledged • {alarm.title}"
        message = (
            f"{alarm.ro_asset.asset_id}: ARI team has acknowledged this RO alarm."
        )
        priority = "NORMAL"
    else:
        title = alarm.title
        message = alarm.message or (
            f"{alarm.ro_asset.asset_id} requires attention."
        )
        priority = alarm.severity

    for recipient in _alarm_recipients(alarm):
        upsert_notification(
            recipient,
            f"ro-alarm:{alarm.id}:{event}",
            title,
            message,
            category="SERVICE",
            priority=priority,
            action="NOTIFICATIONS",
            action_label="View alert",
            metadata={
                "ro_alarm_id": alarm.id,
                "asset_id": alarm.ro_asset.asset_id,
                "alarm_type": alarm.alarm_type,
                "alarm_status": alarm.status,
            },
        )


def _default_manual_severity(alarm_type):
    if alarm_type == "LEAKAGE":
        return "HIGH"
    if alarm_type in {"TDS", "LOW_FLOW"}:
        return "HIGH"
    return "NORMAL"


def _source_for_user(user):
    role = user_role(user)
    if role == "CUSTOMER":
        return "CUSTOMER"
    if role == "ENGINEER":
        return "ENGINEER"
    return "STAFF"


def _resolve_stale_system_alarms(asset, active_keys, actor):
    stale = ROAlarm.objects.filter(
        ro_asset=asset,
        source="SYSTEM",
        alarm_type__in=["SERVICE_DUE", "FILTER_DUE", "TDS"],
        status__in=["OPEN", "ACKNOWLEDGED"],
    )
    if active_keys:
        stale = stale.exclude(dedupe_key__in=active_keys)
    resolved = []
    now = timezone.now()
    for alarm in stale:
        alarm.status = "RESOLVED"
        alarm.resolved_by = actor
        alarm.resolved_at = now
        alarm.save(
            update_fields=[
                "status",
                "resolved_by",
                "resolved_at",
                "updated_at",
            ]
        )
        _notify_alarm(alarm, "resolved")
        resolved.append(alarm.id)
    return resolved


class ROAssetListAPIView(generics.ListAPIView):

    serializer_class = ROAssetSerializer

    permission_classes = [IsOperationsUser]

    def get_queryset(self):

        queryset = ROAsset.objects.select_related(
            "ro_model",
            "current_customer",
        )

        # Sirf available machines
        queryset = queryset.filter(
            status="WAREHOUSE",
            is_active=True,
        )

        keyword = self.request.GET.get("q")

        if keyword:

            queryset = queryset.filter(

                Q(asset_id__icontains=keyword) |

                Q(serial_number__icontains=keyword) |

                Q(ro_model__model_name__icontains=keyword)

            )

        return queryset.order_by("asset_id")


class ROAlarmAssetListAPIView(generics.ListAPIView):
    serializer_class = ROAlarmAssetSerializer
    permission_classes = [IsVerifiedCustomerOrOperations]

    def get_queryset(self):
        return _scoped_assets(self.request).filter(
            current_customer__isnull=False,
        ).order_by("asset_id")


class ROAlarmAssetSettingsAPIView(generics.UpdateAPIView):
    serializer_class = ROAlarmAssetSerializer
    permission_classes = [IsStaffOperator]
    http_method_names = ["patch"]

    def get_queryset(self):
        return _scoped_assets(self.request).filter(
            current_customer__isnull=False,
        )


class ROAlarmListCreateAPIView(APIView):
    permission_classes = [IsVerifiedCustomerOrOperations]

    def get(self, request):
        queryset = _scoped_alarms(request)
        alarm_status = str(request.GET.get("status") or "").strip().upper()
        alarm_type = str(request.GET.get("type") or "").strip().upper()
        if alarm_status in dict(ROAlarm.STATUS_CHOICES):
            queryset = queryset.filter(status=alarm_status)
        if alarm_type in dict(ROAlarm.TYPE_CHOICES):
            queryset = queryset.filter(alarm_type=alarm_type)
        return Response(ROAlarmSerializer(queryset[:200], many=True).data)

    def post(self, request):
        alarm_type = str(request.data.get("alarm_type") or "").strip().upper()
        if alarm_type not in MANUAL_ALARM_TYPES:
            return Response(
                {"detail": "Choose a reportable RO alarm type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assets = _scoped_assets(request).filter(current_customer__isnull=False)
        asset_id = request.data.get("ro_asset")
        if asset_id not in (None, ""):
            asset = get_object_or_404(assets, pk=asset_id)
        else:
            matches = list(assets[:2])
            if len(matches) != 1:
                return Response(
                    {"detail": "Select the RO asset for this alarm."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            asset = matches[0]

        message = str(request.data.get("message") or "").strip()
        observed_value = request.data.get("observed_value")
        if observed_value in ("", None):
            observed_value = None
        elif alarm_type != "TDS":
            observed_value = None
        else:
            try:
                observed_value = int(observed_value)
                if observed_value < 0:
                    raise ValueError
            except (TypeError, ValueError):
                return Response(
                    {"detail": "TDS reading must be a positive whole number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        severity = _default_manual_severity(alarm_type)
        if user_role(request.user) in {"ADMIN", "MANAGER", "OFFICE"}:
            requested_severity = str(
                request.data.get("severity") or ""
            ).strip().upper()
            if requested_severity in dict(ROAlarm.SEVERITY_CHOICES):
                severity = requested_severity

        alarm = ROAlarm.objects.create(
            ro_asset=asset,
            alarm_type=alarm_type,
            severity=severity,
            source=_source_for_user(request.user),
            title=ALARM_TITLE[alarm_type],
            message=message,
            observed_value=observed_value,
            created_by=request.user,
        )
        _notify_alarm(alarm, "open")
        return Response(
            ROAlarmSerializer(alarm).data,
            status=status.HTTP_201_CREATED,
        )


class ROAlarmStatusAPIView(APIView):
    permission_classes = [IsOperationsUser]

    def post(self, request, pk):
        alarm = get_object_or_404(_scoped_alarms(request), pk=pk)
        action = str(request.data.get("action") or "").strip().upper()
        now = timezone.now()

        if action == "ACKNOWLEDGE":
            if alarm.status == "RESOLVED":
                return Response(
                    {"detail": "Resolved alarms cannot be acknowledged."},
                    status=status.HTTP_409_CONFLICT,
                )
            alarm.status = "ACKNOWLEDGED"
            alarm.acknowledged_by = request.user
            alarm.acknowledged_at = now
            alarm.save(
                update_fields=[
                    "status",
                    "acknowledged_by",
                    "acknowledged_at",
                    "updated_at",
                ]
            )
            _notify_alarm(alarm, "acknowledged")
        elif action == "RESOLVE":
            alarm.status = "RESOLVED"
            alarm.resolved_by = request.user
            alarm.resolved_at = now
            alarm.save(
                update_fields=[
                    "status",
                    "resolved_by",
                    "resolved_at",
                    "updated_at",
                ]
            )
            _notify_alarm(alarm, "resolved")
        else:
            return Response(
                {"detail": "Action must be ACKNOWLEDGE or RESOLVE."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(ROAlarmSerializer(alarm).data)


class ROAlarmRefreshAPIView(APIView):
    permission_classes = [IsStaffOperator]

    def post(self, request):
        try:
            horizon_days = int(request.data.get("horizon_days", 7))
        except (TypeError, ValueError):
            horizon_days = 7
        horizon_days = max(0, min(horizon_days, 30))

        today = timezone.localdate()
        horizon = today + timedelta(days=horizon_days)
        assets = _scoped_assets(request).filter(
            current_customer__isnull=False,
            alarm_monitoring_enabled=True,
        )

        from service.models import Service

        created = 0
        existing = 0
        auto_resolved = 0
        scanned = 0

        for asset in assets.iterator():
            scanned += 1
            active_keys = set()
            latest_service = (
                Service.objects.filter(
                    ro_asset=asset,
                    status="COMPLETED",
                )
                .order_by("-completed_date", "-id")
                .first()
            )

            if (
                latest_service is not None
                and latest_service.next_service_date is not None
                and latest_service.next_service_date <= horizon
            ):
                due = latest_service.next_service_date
                key = f"ro-service-due:{asset.id}:{due.isoformat()}"
                active_keys.add(key)
                overdue = due < today
                alarm, was_created = ROAlarm.objects.get_or_create(
                    dedupe_key=key,
                    defaults={
                        "ro_asset": asset,
                        "alarm_type": "SERVICE_DUE",
                        "severity": "HIGH" if overdue else "NORMAL",
                        "source": "SYSTEM",
                        "title": "RO service overdue" if overdue else "RO service due soon",
                        "message": (
                            f"Scheduled RO service date is {due:%d %b %Y}. "
                            "Please plan service attention."
                        ),
                        "due_date": due,
                    },
                )
                if was_created:
                    created += 1
                    _notify_alarm(alarm, "open")
                else:
                    existing += 1

            if (
                asset.next_filter_change_date is not None
                and asset.next_filter_change_date <= horizon
            ):
                due = asset.next_filter_change_date
                key = f"ro-filter-due:{asset.id}:{due.isoformat()}"
                active_keys.add(key)
                overdue = due < today
                alarm, was_created = ROAlarm.objects.get_or_create(
                    dedupe_key=key,
                    defaults={
                        "ro_asset": asset,
                        "alarm_type": "FILTER_DUE",
                        "severity": "HIGH" if overdue else "NORMAL",
                        "source": "SYSTEM",
                        "title": "RO filter change overdue" if overdue else "RO filter change due soon",
                        "message": (
                            f"Planned filter-change date is {due:%d %b %Y}. "
                            "Inspect filter condition and service history before replacement."
                        ),
                        "due_date": due,
                    },
                )
                if was_created:
                    created += 1
                    _notify_alarm(alarm, "open")
                else:
                    existing += 1

            threshold = asset.output_tds_attention_level
            if (
                threshold is not None
                and latest_service is not None
                and latest_service.output_tds is not None
                and latest_service.output_tds >= threshold
            ):
                key = (
                    f"ro-tds-attention:{asset.id}:{latest_service.id}:"
                    f"{threshold}"
                )
                active_keys.add(key)
                alarm, was_created = ROAlarm.objects.get_or_create(
                    dedupe_key=key,
                    defaults={
                        "ro_asset": asset,
                        "alarm_type": "TDS",
                        "severity": "HIGH",
                        "source": "SYSTEM",
                        "title": "TDS reading needs maintenance attention",
                        "message": (
                            f"Latest recorded output TDS is "
                            f"{latest_service.output_tds}; configured attention "
                            f"level is {threshold}. Inspect the RO and service "
                            "history. This alert is not a water-safety determination."
                        ),
                        "observed_value": latest_service.output_tds,
                    },
                )
                if was_created:
                    created += 1
                    _notify_alarm(alarm, "open")
                else:
                    existing += 1

            auto_resolved += len(
                _resolve_stale_system_alarms(
                    asset,
                    active_keys,
                    request.user,
                )
            )

        return Response(
            {
                "scanned_assets": scanned,
                "created": created,
                "existing": existing,
                "auto_resolved": auto_resolved,
                "horizon_days": horizon_days,
                "generated_at": timezone.now(),
            }
        )
