from rest_framework import viewsets

from accounts.permissions import IsReadOnlyOrStaffOperator
from .models import PartCategory, PartMaster
from .serializers import PartCategorySerializer, PartMasterSerializer


class PartCategoryViewSet(viewsets.ModelViewSet):
    queryset = PartCategory.objects.all()
    serializer_class = PartCategorySerializer
    permission_classes = [IsReadOnlyOrStaffOperator]


class PartMasterViewSet(viewsets.ModelViewSet):
    queryset = PartMaster.objects.select_related("category")
    serializer_class = PartMasterSerializer
    permission_classes = [IsReadOnlyOrStaffOperator]
