from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "phone",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "is_verified",
        ]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

class CustomerRegisterSerializer(serializers.Serializer):

    first_name = serializers.CharField(
        max_length=100
    )

    last_name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    phone = serializers.CharField(
        max_length=10,
        min_length=10,
    )

    password = serializers.CharField(
        write_only=True,
        min_length=6,
    )

    def validate_phone(self, value):

        value = value.strip()

        if not value.isdigit():
            raise serializers.ValidationError(
                "Phone number must contain only digits."
            )

        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError(
                "A user with this phone number already exists."
            )

        return value

    def create(self, validated_data):

        return User.objects.create_user(
            phone=validated_data["phone"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data.get(
                "last_name",
                ""
            ),
            role="CUSTOMER",
            is_verified=False,
        )

