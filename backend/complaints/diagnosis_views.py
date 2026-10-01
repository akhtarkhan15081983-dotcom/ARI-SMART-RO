from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import STAFF_ROLES, user_role
from assets.models import ROAsset
from tenancy.models import CompanyMembership

from .models import Complaint
from service.smart_care import asset_health


POSSIBLE_CAUSES = {
    "NO_WATER": [
        "Inlet water supply or pressure may be unavailable.",
        "An inlet/pre-filter restriction may be reducing flow.",
        "A pump, valve, or control fault may be preventing production.",
    ],
    "LOW_WATER_FLOW": [
        "Inlet pressure may be low.",
        "A sediment/filter stage may be restricted.",
        "A pump or flow-control component may require inspection.",
    ],
    "BAD_TASTE": [
        "A filter or post-carbon stage may be due for verified replacement.",
        "Stored water or inlet-water quality may have changed.",
        "The RO may require sanitization or water-quality checks.",
    ],
    "WATER_LEAKAGE": [
        "An external tube, fitting, housing seal, or tank connection may be leaking.",
        "A pressurized connection may require inspection and isolation.",
        "A recently serviced connection may need re-verification.",
    ],
    "PUMP_PROBLEM": [
        "Power supply, adapter, switch, or pump wiring may require engineer testing.",
        "The pump may be stalled, worn, or operating outside normal pressure.",
        "A control/pressure switch may require inspection.",
    ],
    "NOISE": [
        "The pump may be running under abnormal inlet pressure or vibration.",
        "A loose mounting or tubing contact may be transmitting vibration.",
        "A pump or valve may require mechanical inspection.",
    ],
    "FILTER_PROBLEM": [
        "One or more configured filters may be due or overdue.",
        "Water quality or pressure may have changed since the last verified service.",
        "The actual filter condition should be verified before replacement.",
    ],
    "MEMBRANE_PROBLEM": [
        "Membrane performance may have degraded.",
        "Feed-water pressure or TDS may be outside the expected range.",
        "Flow restrictor or membrane housing conditions may require inspection.",
    ],
    "ELECTRICAL": [
        "Power supply, adapter, switch, wiring, or control components may require testing.",
        "Moisture/leakage may have affected an electrical component.",
        "The unit should remain isolated until an engineer completes electrical checks.",
    ],
    "RO_NOT_WORKING": [
        "Power or inlet-water availability may be preventing startup.",
        "A pump, valve, switch, or controller may require inspection.",
        "A service-due component may be contributing to the symptom.",
    ],
    "AMC_SERVICE": [
        "A configured preventive service interval may be due.",
        "One or more parts may need inspection before deciding on replacement.",
    ],
    "OTHER": [
        "Use the customer symptom, RO Health evidence, and physical inspection to narrow the cause.",
        "Check recent service/replacement history before changing any part.",
    ],
}


class ComplaintDiagnosisAssistAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        complaint = (
            Complaint.objects.select_related(
                "customer",
                "customer__company",
                "engineer",
                "engineer__user",
                "company",
            )
            .filter(pk=pk)
            .first()
        )
        if complaint is None:
            return Response({"detail": "Complaint not found."}, status=404)

        role = user_role(request.user)
        if role == "ENGINEER":
            if complaint.engineer_id is None or complaint.engineer.user_id != request.user.id:
                return Response({"detail": "This complaint is not assigned to you."}, status=403)
        elif role in STAFF_ROLES:
            membership = (
                CompanyMembership.objects.filter(
                    user=request.user,
                    is_active=True,
                    company__is_active=True,
                    company__lifecycle_status="ACTIVE",
                )
                .select_related("company")
                .first()
            )
            if membership is None or complaint.company_id != membership.company_id:
                return Response({"detail": "Complaint is outside your workspace."}, status=403)
        else:
            return Response({"detail": "Diagnosis assist is available to authorized staff only."}, status=403)

        asset = (
            ROAsset.objects.filter(
                current_customer=complaint.customer,
                is_active=True,
            )
            .select_related("ro_model")
            .order_by("-id")
            .first()
        )
        company = complaint.company or complaint.customer.company
        health = asset_health(company, asset) if asset is not None and company is not None else None

        due_parts = []
        recent_replacements = []
        if health is not None:
            for part in health["parts"]:
                if part["health_status"] in {"SERVICE_DUE_SOON", "SERVICE_OVERDUE", "ACTION_REQUIRED"}:
                    due_parts.append({
                        "part_name": part["part_name"],
                        "status": part["health_status"],
                        "next_due_date": part["next_due_date"],
                        "days_remaining": part["days_remaining"],
                        "days_overdue": part["days_overdue"],
                    })
                for replacement in part["verified_replacement_history"][:3]:
                    recent_replacements.append({
                        "part_name": part["part_name"],
                        **replacement,
                    })
            recent_replacements.sort(
                key=lambda item: str(item.get("replaced_at") or ""),
                reverse=True,
            )

        possible = POSSIBLE_CAUSES.get(
            complaint.complaint_type,
            POSSIBLE_CAUSES["OTHER"],
        )
        return Response({
            "complaint_id": complaint.complaint_id,
            "complaint_type": complaint.complaint_type,
            "priority": complaint.priority,
            "customer_symptom": complaint.description,
            "ro": None if asset is None else {
                "asset_id": asset.asset_id,
                "model": asset.ro_model.model_name,
                "health_status": health["overall_status"] if health else None,
            },
            "due_or_attention_parts": due_parts,
            "recent_verified_replacements": recent_replacements[:10],
            "possible_causes": [
                {"label": "POSSIBLE", "text": text}
                for text in possible
            ],
            "inspection_checklist": [
                "Confirm the reported symptom with the customer before changing parts.",
                "Verify inlet water, power, visible leakage, and current operating condition.",
                "Review RO Health due/overdue parts and recent verified replacements.",
                "Measure relevant water-quality/pressure/electrical values using approved service procedure.",
                "Record the engineer's actual diagnosis and evidence before marking Part Replaced.",
            ],
            "final_diagnosis_note": (
                "These are possible causes only. Final diagnosis and any replacement decision "
                "must be made and recorded by the assigned engineer."
            ),
        })
