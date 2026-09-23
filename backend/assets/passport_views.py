from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import STAFF_ROLES, user_role
from customers.models import Customer

from .models import ROAsset
from .serializers import ROAssetSerializer


def _customer_for_user(user):
    customer = Customer.objects.filter(user=user, is_active=True).first()
    if customer is not None:
        return customer
    return Customer.objects.filter(
        phone=getattr(user, "phone", ""),
        user__isnull=True,
        is_active=True,
    ).order_by("id").first()


class ROAssetPassportLookupAPIView(APIView):
    """Resolve a machine QR/serial/asset ID to its Digital RO Passport.

    Operations users can inspect any physical RO. Customers can inspect only a
    machine currently assigned to their own customer record. No public lookup
    is exposed, so scanning an ARI QR does not leak customer information.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        code = str(request.query_params.get("code") or "").strip()
        if not code:
            return Response({"detail": "Scan or enter an RO QR/serial."}, status=400)

        asset = (
            ROAsset.objects
            .select_related("ro_model", "current_customer", "reserved_for_customer")
            .prefetch_related("components__part", "components__inventory_item")
            .filter(
                Q(qr_code=code)
                | Q(serial_number=code)
                | Q(asset_id=code)
                | Q(serial_number=code.removeprefix("ARI-RO:"))
            )
            .filter(is_active=True)
            .first()
        )
        if asset is None:
            return Response({"detail": "RO passport not found for this code."}, status=404)

        role = user_role(request.user)
        if role not in STAFF_ROLES:
            if role != "CUSTOMER":
                return Response({"detail": "RO passport access is restricted."}, status=403)
            customer = _customer_for_user(request.user)
            if customer is None or asset.current_customer_id != customer.id:
                return Response({"detail": "This RO is not linked to your account."}, status=403)

        data = ROAssetSerializer(asset).data
        if role == "CUSTOMER":
            # Purchase cost, supplier invoice and reservation operations are
            # internal inventory data and are intentionally hidden from customers.
            for key in (
                "purchase_price",
                "purchase_invoice",
                "reserved_for_customer",
                "reserved_customer_name",
                "reserved_at",
                "reservation_expires_at",
            ):
                data.pop(key, None)

        return Response({
            "success": True,
            "scope": "CUSTOMER" if role == "CUSTOMER" else "OPERATIONS",
            "passport": data,
        })
