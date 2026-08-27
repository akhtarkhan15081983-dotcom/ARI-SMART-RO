from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsStaffOperator

from .serializers import OCRVerifySerializer, EngineerBagIssueSerializer, MyBagSerializer, PartRequestSerializer, PartCatalogSerializer
from .models import InventoryItem, EngineerBagItem, InventoryAuditLog, PartRequest
from partmaster.models import PartMaster
from employees.models import EmployeeProfile


class EngineerBagIssueAPIView(generics.CreateAPIView):
    serializer_class = EngineerBagIssueSerializer
    permission_classes = [IsStaffOperator]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        inventory_item = get_object_or_404(InventoryItem.objects.select_for_update(), id=request.data.get("inventory_item"))
        if inventory_item.status != "IN_STOCK":
            InventoryAuditLog.objects.create(inventory_item=inventory_item, performed_by=request.user, action="SECURITY_REJECT", old_status=inventory_item.status, new_status=inventory_item.status, serial_number=inventory_item.serial_number or "", remarks="Attempted to issue an inventory item that was not in stock.")
            return Response({"error": "Part is not available in stock."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        engineer = serializer.validated_data["engineer"]
        if EngineerBagItem.objects.filter(inventory_item=inventory_item, status="ISSUED").exists():
            InventoryAuditLog.objects.create(inventory_item=inventory_item, engineer=engineer, performed_by=request.user, action="SECURITY_REJECT", old_status=inventory_item.status, new_status=inventory_item.status, serial_number=inventory_item.serial_number or "", remarks="Duplicate issue attempt detected.")
            return Response({"error": "This physical part is already issued to an engineer."}, status=status.HTTP_400_BAD_REQUEST)
        bag_item = serializer.save(status="ISSUED")
        old_status = inventory_item.status
        inventory_item.status = "ISSUED"
        inventory_item.save(update_fields=["status"])
        InventoryAuditLog.objects.create(inventory_item=inventory_item, engineer=engineer, performed_by=request.user, action="ISSUED", old_status=old_status, new_status="ISSUED", serial_number=inventory_item.serial_number or "", remarks=request.data.get("remarks", ""))
        return Response(EngineerBagIssueSerializer(bag_item).data, status=status.HTTP_201_CREATED)


class OCRVerifyAPIView(generics.GenericAPIView):
    serializer_class = OCRVerifySerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        engineer = serializer.validated_data["engineer"]
        serial_number = serializer.validated_data["serial_number"].strip()
        if engineer.user_id != request.user.id:
            return Response({"verified": False, "message": "You cannot verify a part for another engineer."}, status=status.HTTP_403_FORBIDDEN)
        bag_item = EngineerBagItem.objects.select_related("inventory_item", "inventory_item__part", "engineer__user").filter(engineer=engineer, inventory_item__serial_number=serial_number, inventory_item__status="ISSUED", status="ISSUED").first()
        if not bag_item:
            return Response({"verified": False, "message": "This part is not currently issued to this engineer."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"verified": True, "message": "Part verified successfully.", "inventory_item": bag_item.inventory_item.id, "part": bag_item.inventory_item.part.name, "part_code": bag_item.inventory_item.part.code, "serial_number": bag_item.inventory_item.serial_number})


class MyBagAPIView(generics.ListAPIView):
    serializer_class = MyBagSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EngineerBagItem.objects.select_related("inventory_item__part", "engineer__user").filter(engineer__user=self.request.user, status="ISSUED", inventory_item__status="ISSUED").order_by("-issue_date")


class PartCatalogAPIView(generics.ListAPIView):
    serializer_class = PartCatalogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PartMaster.objects.filter(is_active=True).order_by("name")


class MyPartRequestsAPIView(generics.ListCreateAPIView):
    serializer_class = PartRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PartRequest.objects.select_related("part", "engineer").filter(engineer__user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        engineer = get_object_or_404(EmployeeProfile, user=self.request.user, designation="ENGINEER", is_active=True)
        serializer.save(engineer=engineer)
