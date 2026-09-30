from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from assets.models import ROAsset
from service.models import Service
from service.smart_care import asset_health

from .customer_scope import linked_customer_for_complaints
from .guidance import complaint_guidance, supported_symptoms


class ComplaintAssistantAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        customer = linked_customer_for_complaints(request.user)
        if customer is None:
            return Response({"detail": "Complaint assistant is available to linked customer accounts."}, status=403)

        if not request.GET.get("symptom"):
            return Response({"symptoms": supported_symptoms()})

        guidance = complaint_guidance(request.GET.get("symptom"))
        asset_id = str(request.GET.get("asset_id", "") or "").strip()
        asset = None
        if asset_id:
            asset = (
                ROAsset.objects.filter(
                    asset_id=asset_id,
                    current_customer=customer,
                    is_active=True,
                )
                .select_related("ro_model")
                .first()
            )
            if asset is None:
                return Response({"detail": "RO asset not found for this customer."}, status=404)
        else:
            asset = (
                ROAsset.objects.filter(current_customer=customer, is_active=True)
                .select_related("ro_model")
                .order_by("-id")
                .first()
            )

        context = {
            "customer_reference": customer.customer_id,
            "symptom": guidance["symptom"],
            "complaint_type": guidance["complaint_type"],
            "priority": guidance["priority"],
        }
        health = None
        if asset is not None and customer.company_id is not None:
            health = asset_health(customer.company, asset)
            last_service = (
                Service.objects.filter(
                    customer=customer,
                    ro_asset=asset,
                    status="COMPLETED",
                    completed_date__isnull=False,
                )
                .select_related("engineer__user")
                .order_by("-completed_date", "-id")
                .first()
            )
            context.update({
                "ro_asset_id": asset.asset_id,
                "ro_model": asset.ro_model.model_name,
                "filter_service_health_status": health["overall_status"],
                "last_service_date": last_service.completed_date if last_service else None,
                "replacement_history_summary": [
                    {
                        "part_name": part["part_name"],
                        "latest_replacement": (
                            part["verified_replacement_history"][0]
                            if part["verified_replacement_history"]
                            else None
                        ),
                    }
                    for part in health["parts"]
                    if part["verified_replacement_history"]
                ][:10],
            })

        return Response({
            "guidance": guidance,
            "ro_health": health,
            "complaint_context": context,
            "privacy_note": "Only operational RO/service context is prepared; unnecessary personal data is excluded.",
        })
