from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import PartCategory, PartMaster
from .serializers import (
    PartCategorySerializer,
    PartMasterSerializer,
)


class PartCategoryViewSet(viewsets.ModelViewSet):

    queryset = PartCategory.objects.all()
    serializer_class = PartCategorySerializer
    permission_classes = [IsAuthenticated]


class PartMasterViewSet(viewsets.ModelViewSet):

    queryset = PartMaster.objects.select_related("category")
    serializer_class = PartMasterSerializer
    permission_classes = [IsAuthenticated]