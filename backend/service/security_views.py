from rest_framework.exceptions import ValidationError

from accounts.permissions import user_role
from tenancy.access import request_company

from .views import ServiceCreateAPIView, ServiceUpdateAPIView


PROTECTED_ENGINEER_FIELDS = {"engineer", "customer", "ro_asset", "job"}


def _validate_service_relations(request, validated_data, instance=None):
    role = user_role(request.user)
    company = request_company(request)
    engineer = validated_data.get("engineer", getattr(instance, "engineer", None))
    customer = validated_data.get("customer", getattr(instance, "customer", None))
    ro_asset = validated_data.get("ro_asset", getattr(instance, "ro_asset", None))
    job = validated_data.get("job", getattr(instance, "job", None))

    if company is None:
        raise ValidationError({"detail": "Active company workspace not found."})

    if instance is not None and instance.company_id not in (None, company.id):
        raise ValidationError({"detail": "Service belongs to another company workspace."})

    if engineer is None or engineer.company_id != company.id:
        raise ValidationError({
            "engineer": ["Engineer must belong to the active company workspace."]
        })
    if not engineer.is_active or not engineer.user.is_active:
        raise ValidationError({"engineer": ["Engineer must be active."]})

    if getattr(customer, "company_id", None) not in (None, company.id):
        raise ValidationError({"customer": ["Customer belongs to another company workspace."]})
    if job is not None and getattr(job, "company_id", None) not in (None, company.id):
        raise ValidationError({"job": ["Job belongs to another company workspace."]})

    if ro_asset is not None and ro_asset.current_customer_id not in (None, getattr(customer, "id", None)):
        raise ValidationError({
            "ro_asset": ["RO asset is assigned to a different customer."]
        })

    if role == "ENGINEER" and instance is not None:
        changed = [
            field
            for field in PROTECTED_ENGINEER_FIELDS
            if field in validated_data
            and getattr(instance, f"{field}_id", None)
            != getattr(validated_data[field], "id", None)
        ]
        if changed:
            raise ValidationError({
                "detail": (
                    "Engineers cannot reassign service ownership or linked customer/asset/job."
                ),
                "protected_fields": changed,
            })
    return company


class SecureServiceCreateAPIView(ServiceCreateAPIView):
    def perform_create(self, serializer):
        company = _validate_service_relations(self.request, serializer.validated_data)
        serializer.save(company=company)


class SecureServiceUpdateAPIView(ServiceUpdateAPIView):
    def perform_update(self, serializer):
        company = _validate_service_relations(
            self.request,
            serializer.validated_data,
            instance=self.get_object(),
        )
        serializer.save(company=company)
