from rest_framework import serializers

from .models import Complaint


class ComplaintSerializer(
    serializers.ModelSerializer
):

    customer_name = serializers.CharField(
        source="customer.name",
        read_only=True,
    )

    customer_id_display = serializers.CharField(
        source="customer.customer_id",
        read_only=True,
    )

    customer_phone = serializers.CharField(
        source="customer.phone",
        read_only=True,
    )

    current_card_number = serializers.CharField(
        source="customer.card_number",
        read_only=True,
    )

    old_card_number = serializers.CharField(
        source="customer.old_card_number",
        read_only=True,
    )

    engineer_name = serializers.SerializerMethodField()

    engineer_id_display = serializers.CharField(
        source="engineer.employee_id",
        read_only=True,
    )

    linked_service_id_display = serializers.CharField(
        source="linked_service.service_id",
        read_only=True,
    )

    class Meta:

        model = Complaint

        fields = [
            "id",
            "complaint_id",

            # Customer
            "customer",
            "customer_name",
            "customer_id_display",
            "customer_phone",
            "current_card_number",
            "old_card_number",

            # Engineer
            "engineer",
            "engineer_name",
            "engineer_id_display",

            # Complaint
            "complaint_type",
            "description",
            "priority",
            "status",

            # Dates
            "complaint_date",
            "scheduled_date",
            "resolved_date",

            # Work
            "engineer_remarks",
            "resolution",

            # Location
            "latitude",
            "longitude",

            # Service
            "linked_service",
            "linked_service_id_display",

            # System
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "complaint_id",

            "customer_name",
            "customer_id_display",
            "customer_phone",
            "current_card_number",
            "old_card_number",

            "engineer_name",
            "engineer_id_display",

            "linked_service_id_display",

            "created_at",
            "updated_at",
        ]

    def get_engineer_name(
        self,
        obj,
    ):
        if not obj.engineer:
            return ""

        user = obj.engineer.user

        full_name = (
            user.get_full_name()
            or ""
        ).strip()

        if full_name:
            return full_name

        return (
            getattr(
                user,
                "phone",
                "",
            )
            or obj.engineer.employee_id
        )