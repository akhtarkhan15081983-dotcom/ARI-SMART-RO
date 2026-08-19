from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models.asset import ROAsset
from .serializers import ROAssetSerializer


class ROAssetListAPIView(generics.ListAPIView):

    serializer_class = ROAssetSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        queryset = ROAsset.objects.select_related(
            "ro_model",
            "current_customer",
        )

        # Sirf available machines
        queryset = queryset.filter(
            status="WAREHOUSE",
            is_active=True,
        )

        keyword = self.request.GET.get("q")

        if keyword:

            queryset = queryset.filter(

                Q(asset_id__icontains=keyword) |

                Q(serial_number__icontains=keyword) |

                Q(ro_model__name__icontains=keyword)

            )

        return queryset.order_by("asset_id")