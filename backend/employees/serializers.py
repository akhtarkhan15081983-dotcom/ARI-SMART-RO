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
        read_only_fields = ["last_location_updated", "is_online"]

    def validate_live_latitude(self, value):
        if value < -90 or value > 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_live_longitude(self, value):
        if value < -180 or value > 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value


class EmployeeProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    photo = serializers.SerializerMethodField()
    face_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeProfile
        fields = [
            "employee_id",
            "first_name",
            "last_name",
            "pincode",
            "emergency_name",
            "emergency_contact",
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
            "face_enrolled",
            "face_enrolled_at",
            "face_enrollment_verified",
            "attendance_device_id",
        ]
        read_only_fields = [
            "face_enrolled_at",
            "face_enrollment_verified",
            "attendance_device_id",
        ]

    def get_photo(self, obj):
        request = self.context.get("request")
        if obj.photo:
            return request.build_absolute_uri(obj.photo.url)
        return None

    def get_face_enrolled(self, obj):
        return bool(obj.face_enrolled_at and obj.photo)


class EmployeeProfileUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name", required=False)
    last_name = serializers.CharField(source="user.last_name", required=False)
    email = serializers.EmailField(source="user.email", required=False)

    class Meta:
        model = EmployeeProfile
        fields = [
            "first_name",
            "last_name",
            "email",
            "address",
            "city",
            "state",
            "pincode",
            "emergency_name",
            "emergency_contact",
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        for key, value in user_data.items():
            setattr(instance.user, key, value)
        instance.user.save()

        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance


class AssignmentEmployeeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.get_full_name", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = EmployeeProfile
        fields = [
            "id",
            "employee_id",
            "name",
            "phone",
            "role",
            "designation",
        ]
