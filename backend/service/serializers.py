from rest_framework import serializers

from .models import (
    Service,
    ServicePart,
    ServicePhoto,
    ServiceSignature,
)


class ServiceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Service
        fields = "__all__"


class ServicePartSerializer(serializers.ModelSerializer):

    class Meta:
        model = ServicePart
        fields = "__all__"


class ServicePhotoSerializer(serializers.ModelSerializer):

    class Meta:
        model = ServicePhoto
        fields = "__all__"


class ServiceSignatureSerializer(serializers.ModelSerializer):

    class Meta:
        model = ServiceSignature
        fields = "__all__"