from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .serializers import OCRVerifySerializer,EngineerBagIssueSerializer

from .models import InventoryItem, EngineerBagItem
from rest_framework.permissions import IsAuthenticated
from .serializers import MyBagSerializer


class EngineerBagIssueAPIView(generics.CreateAPIView):

    serializer_class = EngineerBagIssueSerializer

    def create(self, request, *args, **kwargs):

        inventory_item = InventoryItem.objects.get(
            id=request.data["inventory_item"]
        )

        if inventory_item.status != "IN_STOCK":
            return Response(
                {
                    "error": "Part is not available in stock."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bag_item = serializer.save()

        inventory_item.status = "ISSUED"
        inventory_item.save()

        return Response(
            EngineerBagIssueSerializer(bag_item).data,
            status=status.HTTP_201_CREATED
        )


class OCRVerifyAPIView(generics.GenericAPIView):

    serializer_class = OCRVerifySerializer

    def post(self, request):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        engineer = serializer.validated_data["engineer"]
        serial_number = serializer.validated_data["serial_number"]
        print("LOGIN ENGINEER :", engineer)
        print("SCANNED SERIAL :", serial_number)

        try:

            print(
                EngineerBagItem.objects.filter(
                    inventory_item__serial_number=serial_number
                ).values(
                    "engineer__user__first_name",
                    "status",
                    "inventory_item__serial_number"
                )
            )

            bag_item = EngineerBagItem.objects.get(
                engineer=engineer,
                inventory_item__serial_number=serial_number,
                status="ISSUED"
            )
            return Response({
                "verified": True,
                "message": "Part verified successfully.",
                "inventory_item": bag_item.inventory_item.id,
                "part": bag_item.inventory_item.part.name,
            })

        except EngineerBagItem.DoesNotExist:

            return Response({
                "verified": False,
                "message": "This part is not issued to this engineer."
            }, status=status.HTTP_400_BAD_REQUEST)


class MyBagAPIView(generics.ListAPIView):

    serializer_class = MyBagSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        return EngineerBagItem.objects.select_related(
            "inventory_item__part",
            "engineer__user",
        ).filter(
            engineer__user=self.request.user,
            status="ISSUED",
        )