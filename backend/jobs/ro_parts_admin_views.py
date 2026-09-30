from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import user_role
from assets.models.asset import ROAlarm, ROAsset
from customers.models import Customer
from tenancy.access import request_company

from .ro_parts_views import _asset_passport_payload


class AdminROPartsPassportAPIView(APIView):
    """Tenant-scoped Digital RO register for company administrators."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if user_role(request.user) != "ADMIN":
            return Response(
                {"detail": "Only admin can view all customer Digital RO passports."},
                status=status.HTTP_403_FORBIDDEN,
            )

        company = request_company(request)
        if company is None:
            return Response(
                {"detail": "Admin account is not linked to an active company."},
                status=status.HTTP_403_FORBIDDEN,
            )

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

        rows = []
        total_active_alarms = 0
        for customer in customers[:250]:
            assets = (
                ROAsset.objects.filter(current_customer=customer, is_active=True)
                .select_related("ro_model")
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
                "customer_count": len(rows),
                "active_alarm_count": total_active_alarms,
                "customers": rows,
            }
        )
