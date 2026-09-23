from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrManager, IsOperationsUser, IsStaffOperator
from customers.models import Customer, PublicCustomerRequest
from products.models import ROModel

from .models import ROAsset, ROAssetMovement
from .serializers import ROAssetMovementSerializer, ROAssetSerializer


def _clean_serial(value):
    return str(value or "").strip()[:100]


def _movement(*, asset, action, user, customer=None, request_row=None, old_status="", remarks=""):
    return ROAssetMovement.objects.create(
        asset=asset,
        action=action,
        customer=customer,
        request_id=getattr(request_row, "id", None),
        request_number=str(getattr(request_row, "request_number", "") or ""),
        from_status=old_status,
        to_status=asset.status,
        performed_by=user,
        remarks=str(remarks or "")[:1000],
    )


class ROAssetListAPIView(generics.ListAPIView):
    serializer_class = ROAssetSerializer
    permission_classes = [IsOperationsUser]

    def get_queryset(self):
        queryset = ROAsset.objects.select_related("ro_model", "current_customer")
        status_value = str(self.request.GET.get("status", "") or "").strip().upper()
        if status_value:
            queryset = queryset.filter(status=status_value)
        keyword = str(self.request.GET.get("q", "") or "").strip()
        if keyword:
            queryset = queryset.filter(
                Q(asset_id__icontains=keyword)
                | Q(serial_number__icontains=keyword)
                | Q(ro_model__model_name__icontains=keyword)
                | Q(current_customer__name__icontains=keyword)
            )
        return queryset.filter(is_active=True).order_by("asset_id")


class ROAssetWorkflowSummaryAPIView(APIView):
    permission_classes = [IsStaffOperator]

    def get(self, request):
        by_status = {
            row["status"]: row["count"]
            for row in ROAsset.objects.filter(is_active=True)
            .values("status")
            .annotate(count=Count("id"))
        }
        return Response(
            {
                "summary": {
                    "total": sum(by_status.values()),
                    "warehouse": by_status.get("WAREHOUSE", 0),
                    "assigned": by_status.get("ASSIGNED", 0),
                    "installed": by_status.get("INSTALLED", 0),
                    "returned": by_status.get("RETURNED", 0),
                    "repair": by_status.get("REPAIR", 0),
                    "scrap": by_status.get("SCRAP", 0),
                    "sale_allocated": ROAsset.objects.filter(
                        is_active=True, deployment_type="SALE"
                    ).count(),
                    "rent_allocated": ROAsset.objects.filter(
                        is_active=True, deployment_type="RENT"
                    ).count(),
                }
            }
        )


class ROAssetReceiveAPIView(APIView):
    permission_classes = [IsStaffOperator]

    @transaction.atomic
    def post(self, request):
        try:
            model_id = int(request.data.get("ro_model"))
        except (TypeError, ValueError):
            return Response({"detail": "Select a valid RO model."}, status=400)
        ro_model = ROModel.objects.select_for_update().filter(pk=model_id, is_active=True).first()
        if ro_model is None:
            return Response({"detail": "RO model not found or inactive."}, status=404)

        raw_serials = request.data.get("serial_numbers")
        if isinstance(raw_serials, str):
            raw_serials = raw_serials.replace(",", "\n").splitlines()
        if not isinstance(raw_serials, list):
            return Response({"detail": "Provide serial_numbers as a list or one-per-line text."}, status=400)
        serials = [_clean_serial(v) for v in raw_serials if _clean_serial(v)]
        if not serials:
            return Response({"detail": "At least one RO serial number is required."}, status=400)
        if len(serials) != len(set(serials)):
            return Response({"detail": "Duplicate serial numbers were entered in this receipt."}, status=400)
        existing = set(
            ROAsset.objects.filter(serial_number__in=serials).values_list("serial_number", flat=True)
        )
        if existing:
            return Response(
                {"detail": f"Already registered serial(s): {', '.join(sorted(existing)[:8])}"},
                status=409,
            )

        invoice = str(request.data.get("purchase_invoice", "") or "").strip()[:100]
        purchase_date = request.data.get("purchase_date") or timezone.localdate()
        try:
            purchase_price = Decimal(str(request.data.get("purchase_price", 0) or 0))
            if purchase_price < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            return Response({"detail": "Enter a valid purchase price."}, status=400)

        assets = []
        for serial in serials:
            asset = ROAsset.objects.create(
                ro_model=ro_model,
                serial_number=serial,
                qr_code=f"ARI-RO:{serial}",
                status="WAREHOUSE",
                purchase_date=purchase_date,
                purchase_invoice=invoice,
                purchase_price=purchase_price,
            )
            _movement(
                asset=asset,
                action="RECEIVED",
                user=request.user,
                old_status="",
                remarks=f"Received into warehouse. Invoice {invoice}".strip(),
            )
            assets.append(asset)

        ro_model.stock_quantity = ROAsset.objects.filter(
            ro_model=ro_model, status="WAREHOUSE", is_active=True
        ).count()
        ro_model.save(update_fields=["stock_quantity"])
        return Response(
            {
                "success": True,
                "received": len(assets),
                "stock_quantity": ro_model.stock_quantity,
                "assets": ROAssetSerializer(assets, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ROAssetAllocateAPIView(APIView):
    permission_classes = [IsAdminOrManager]

    @transaction.atomic
    def post(self, request, asset_id):
        asset = (
            ROAsset.objects.select_for_update()
            .select_related("ro_model", "current_customer")
            .filter(pk=asset_id, is_active=True)
            .first()
        )
        if asset is None:
            return Response({"detail": "RO asset not found."}, status=404)
        if asset.status != "WAREHOUSE" or asset.current_customer_id is not None:
            return Response({"detail": "This RO is not available in warehouse stock."}, status=409)

        mode = str(request.data.get("deployment_type", "") or "").strip().upper()
        if mode not in {"SALE", "RENT"}:
            return Response({"detail": "deployment_type must be SALE or RENT."}, status=400)
        try:
            customer_id = int(request.data.get("customer_id"))
        except (TypeError, ValueError):
            return Response({"detail": "Select a valid customer."}, status=400)
        customer = Customer.objects.select_for_update().filter(pk=customer_id, is_active=True).first()
        if customer is None:
            return Response({"detail": "Active customer not found."}, status=404)

        request_row = None
        raw_request_id = request.data.get("request_id")
        if raw_request_id not in (None, ""):
            try:
                request_row = PublicCustomerRequest.objects.select_for_update().get(pk=int(raw_request_id))
            except (ValueError, PublicCustomerRequest.DoesNotExist):
                return Response({"detail": "Customer purchase/rental request not found."}, status=404)
            expected = "PURCHASE" if mode == "SALE" else "RENTAL"
            if request_row.request_type != expected:
                return Response({"detail": f"Selected request is not a {expected.lower()} request."}, status=409)
            if request_row.product_id and request_row.product_id != asset.ro_model_id:
                return Response({"detail": "Requested RO model does not match this physical RO."}, status=409)
            request_row.existing_customer = customer
            request_row.status = "CONFIRMED"
            request_row.save(update_fields=["existing_customer", "status", "updated_at"])

        old_status = asset.status
        asset.status = "ASSIGNED"
        asset.deployment_type = mode
        asset.current_customer = customer
        asset.assigned_at = timezone.now()
        asset.save(update_fields=["status", "deployment_type", "current_customer", "assigned_at"])

        customer.ro_model = asset.ro_model.model_name
        customer.ownership_type = "PURCHASE" if mode == "SALE" else "RENTAL"
        if mode == "RENT":
            customer.monthly_rent = asset.ro_model.monthly_rent
            customer.security_deposit = asset.ro_model.security_deposit
            customer.installation_charge = asset.ro_model.installation_charge
        customer.save(
            update_fields=[
                "ro_model",
                "ownership_type",
                "monthly_rent",
                "security_deposit",
                "installation_charge",
            ]
        )

        asset.ro_model.stock_quantity = ROAsset.objects.filter(
            ro_model=asset.ro_model, status="WAREHOUSE", is_active=True
        ).count()
        asset.ro_model.save(update_fields=["stock_quantity"])
        _movement(
            asset=asset,
            action="SALE_ALLOCATED" if mode == "SALE" else "RENT_ALLOCATED",
            user=request.user,
            customer=customer,
            request_row=request_row,
            old_status=old_status,
            remarks=request.data.get("remarks", ""),
        )
        return Response(
            {
                "success": True,
                "message": f"RO {asset.asset_id} allocated for {mode.lower()}.",
                "asset": ROAssetSerializer(asset).data,
                "stock_quantity": asset.ro_model.stock_quantity,
            }
        )


class ROAssetReturnAPIView(APIView):
    permission_classes = [IsAdminOrManager]

    @transaction.atomic
    def post(self, request, asset_id):
        asset = (
            ROAsset.objects.select_for_update()
            .select_related("ro_model", "current_customer")
            .filter(pk=asset_id, is_active=True)
            .first()
        )
        if asset is None:
            return Response({"detail": "RO asset not found."}, status=404)
        if asset.deployment_type != "RENT" or asset.status not in {"ASSIGNED", "INSTALLED", "SERVICE", "REPAIR"}:
            return Response({"detail": "Only an active rental RO can be returned."}, status=409)
        old_status = asset.status
        customer = asset.current_customer
        asset.status = "RETURNED"
        asset.save(update_fields=["status"])
        _movement(
            asset=asset,
            action="RENT_RETURNED",
            user=request.user,
            customer=customer,
            old_status=old_status,
            remarks=request.data.get("remarks", ""),
        )
        return Response({"success": True, "asset": ROAssetSerializer(asset).data})


class ROAssetRestockAPIView(APIView):
    permission_classes = [IsAdminOrManager]

    @transaction.atomic
    def post(self, request, asset_id):
        asset = (
            ROAsset.objects.select_for_update()
            .select_related("ro_model", "current_customer")
            .filter(pk=asset_id, is_active=True)
            .first()
        )
        if asset is None:
            return Response({"detail": "RO asset not found."}, status=404)
        if asset.status not in {"RETURNED", "REFURBISHED"}:
            return Response({"detail": "Only returned/refurbished RO can be restocked."}, status=409)
        old_status = asset.status
        customer = asset.current_customer
        asset.status = "WAREHOUSE"
        asset.deployment_type = ""
        asset.current_customer = None
        asset.assigned_at = None
        asset.save(update_fields=["status", "deployment_type", "current_customer", "assigned_at"])
        asset.ro_model.stock_quantity = ROAsset.objects.filter(
            ro_model=asset.ro_model, status="WAREHOUSE", is_active=True
        ).count()
        asset.ro_model.save(update_fields=["stock_quantity"])
        _movement(
            asset=asset,
            action="RESTOCKED",
            user=request.user,
            customer=customer,
            old_status=old_status,
            remarks=request.data.get("remarks", ""),
        )
        return Response(
            {
                "success": True,
                "asset": ROAssetSerializer(asset).data,
                "stock_quantity": asset.ro_model.stock_quantity,
            }
        )


class ROAssetMovementListAPIView(generics.ListAPIView):
    serializer_class = ROAssetMovementSerializer
    permission_classes = [IsStaffOperator]

    def get_queryset(self):
        queryset = ROAssetMovement.objects.select_related(
            "asset__ro_model", "customer", "performed_by"
        )
        raw_asset = self.request.GET.get("asset_id")
        if str(raw_asset or "").isdigit():
            queryset = queryset.filter(asset_id=int(raw_asset))
        return queryset[:500]
