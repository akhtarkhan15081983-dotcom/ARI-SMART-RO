from rest_framework import serializers
from .models import EmployeeProfile


class EmployeeLocationSerializer(serializers.ModelSerializer):

    live_latitude = serializers.DecimalField(
        source="last_latitude",
        max_digits=10,
        decimal_places=7,
        required=False,
    )

    live_longitude = serializers.DecimalField(
        source="last_longitude",
        max_digits=10,
        decimal_places=7,
        required=False,
    )

    class Meta:
        model = EmployeeProfile
        fields = [
            "live_latitude",
            "live_longitude",
            "last_location_updated",
            "is_online",
        ]

class EmployeeProfileSerializer(serializers.ModelSerializer):

    full_name = serializers.CharField(
        source="user.get_full_name",
        read_only=True,
    )

    phone = serializers.CharField(
        source="user.phone",
        read_only=True,
    )

    email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    role = serializers.CharField(
        source="user.role",
        read_only=True,
    )

    photo = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeProfile

        fields = [

            "employee_id",

            "full_name",

            "phone",

            "email",

            "role",

            "designation",

            "joining_date",

            "gender",

            "city",

            "state",

            "address",

            "photo",

        ]

    def get_photo(self, obj):

        request = self.context.get("request")

        if obj.photo:

            return request.build_absolute_uri(
                obj.photo.url
            )

        return None

class EmployeeProfileUpdateSerializer(serializers.ModelSerializer):

    email = serializers.EmailField(
        source="user.email",
        required=False,
    )

    class Meta:
        model = EmployeeProfile
        fields = [
            "email",
            "city",
            "state",
            "address",
            "emergency_contact",
            "emergency_name",
        ]

    def update(self, instance, validated_data):

        user_data = validated_data.pop("user", None)

        if user_data:
            instance.user.email = user_data.get(
                "email",
                instance.user.email,
            )
            instance.user.save()

        return super().update(
            instance,
            validated_data,
        )
