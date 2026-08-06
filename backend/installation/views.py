from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from .models import InstallationPart, Installation
from .serializers import (
    InstallationPartSerializer,
    InstallationSerializer,
)


class InstallationCreateAPIView(generics.CreateAPIView):
    queryset = Installation.objects.all()
    serializer_class = InstallationSerializer


class InstallationPartCreateAPIView(generics.CreateAPIView):
    queryset = InstallationPart.objects.all()
    serializer_class = InstallationPartSerializer


class CompleteInstallationAPIView(generics.CreateAPIView):
    serializer_class = InstallationSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        engineer = request.user.employee_profile

        installation = serializer.save(
            engineer=engineer,
            status="COMPLETED",
            completed_date=timezone.now(),
            business_type="RENT",
        )

        return Response(
            {
                "success": True,
                "installation_id": installation.installation_id,
                "message": "Installation completed successfully.",
            },
            status=status.HTTP_201_CREATED,
        )