from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from assets.models import ROAsset
from service.models import Service
from service.smart_care import asset_health

from .customer_scope import linked_customer_for_complaints
from .guidance import complaint_guidance, supported_symptoms
from .serializers import ComplaintSerializer


class ComplaintAssistantAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _customer(self, request):
        return linked_customer_for_complaints(request.user)

    def _asset(self, customer, asset_id):
        asset_id = str(asset_id or "").strip()
        queryset = ROAsset.objects.filter(
            current_customer=customer,
            is_active=True,
        ).select_related("ro_model")
        if asset_id:
            return queryset.filter(asset_id=asset_id).first()
        return queryset.order_by("-id").first()

    def _context(self, customer, guidance, asset):
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
        return context, health

    def get(self, request):
        customer = self._customer(request)
        if customer is None:
            return Response({"detail": "Complaint assistant is available to linked customer accounts."}, status=403)

        if not request.GET.get("symptom"):
            return Response({"symptoms": supported_symptoms()})

        guidance = complaint_guidance(request.GET.get("symptom"))
        requested_asset_id = str(request.GET.get("asset_id", "") or "").strip()
        asset = self._asset(customer, requested_asset_id)
        if requested_asset_id and asset is None:
            return Response({"detail": "RO asset not found for this customer."}, status=404)

        context, health = self._context(customer, guidance, asset)
        return Response({
            "guidance": guidance,
            "ro_health": health,
            "complaint_context": context,
            "privacy_note": "Only operational RO/service context is prepared; unnecessary personal data is excluded.",
        })

    def post(self, request):
        customer = self._customer(request)
        if customer is None:
            return Response({"detail": "Complaint assistant is available to linked customer accounts."}, status=403)

        symptom = str(request.data.get("symptom", "") or "").strip()
        if not symptom:
            return Response({"detail": "Select a symptom before raising the complaint."}, status=400)
        guidance = complaint_guidance(symptom)

        requested_asset_id = str(request.data.get("asset_id", "") or "").strip()
        asset = self._asset(customer, requested_asset_id)
        if requested_asset_id and asset is None:
            return Response({"detail": "RO asset not found for this customer."}, status=404)
        context, _ = self._context(customer, guidance, asset)

        description = str(request.data.get("description", "") or "").strip()
        if len(description) < 3:
            description = guidance["label"]

        context_lines = [
            "Guided Complaint Context:",
            f"Symptom: {guidance['label']}",
            f"Customer Ref: {customer.customer_id}",
        ]
        if context.get("ro_asset_id"):
            context_lines.append(f"RO Asset: {context['ro_asset_id']}")
        if context.get("ro_model"):
            context_lines.append(f"RO Model: {context['ro_model']}")
        if context.get("filter_service_health_status"):
            context_lines.append(f"RO Health: {context['filter_service_health_status']}")
        if context.get("last_service_date"):
            context_lines.append(f"Last Service: {context['last_service_date']}")
        context_lines.append(f"Customer Description: {description}")

        serializer = ComplaintSerializer(data={
            "customer": customer.id,
            "complaint_type": guidance["complaint_type"],
            "description": "\n".join(context_lines),
            "priority": guidance["priority"],
            "latitude": customer.latitude,
            "longitude": customer.longitude,
        })
        serializer.is_valid(raise_exception=True)
        complaint = serializer.save(
            customer=customer,
            company=customer.company,
            engineer=None,
            priority=guidance["priority"],
            latitude=customer.latitude,
            longitude=customer.longitude,
        )
        return Response(
            {
                "success": True,
                "message": "Complaint raised successfully.",
                "complaint": ComplaintSerializer(complaint).data,
                "guidance": guidance,
            },
            status=201,
        )
