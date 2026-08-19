from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Service
from .serializers import ServiceSerializer
from django.db.models import Q

import openpyxl


class ServiceListAPIView(generics.ListAPIView):

    queryset = Service.objects.all().order_by("-id")

    serializer_class = ServiceSerializer

    permission_classes = [IsAuthenticated]


class ServiceCreateAPIView(generics.CreateAPIView):

    queryset = Service.objects.all()

    serializer_class = ServiceSerializer

    permission_classes = [IsAuthenticated]


class ServiceDetailAPIView(generics.RetrieveAPIView):

    queryset = Service.objects.all()

    serializer_class = ServiceSerializer

    permission_classes = [IsAuthenticated]


class ServiceUpdateAPIView(generics.UpdateAPIView):

    queryset = Service.objects.all()

    serializer_class = ServiceSerializer

    permission_classes = [IsAuthenticated]


class CompleteServiceAPIView(generics.UpdateAPIView):

    queryset = Service.objects.all()

    serializer_class = ServiceSerializer

    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):

        service = self.get_object()

        service.status = "COMPLETED"

        service.completed_date = timezone.now()

        service.save()

        return Response(
            {
                "success": True,
                "service_id": service.service_id,
                "message": "Service completed successfully.",
            },
            status=status.HTTP_200_OK,
        )

class ServiceSearchAPIView(generics.ListAPIView):

    serializer_class = ServiceSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        keyword = self.request.GET.get("q", "")

        queryset = Service.objects.select_related(
            "customer",
            "engineer",
            "ro_asset",
        )

        if keyword:

            queryset = queryset.filter(

                Q(service_id__icontains=keyword) |

                Q(customer__name__icontains=keyword) |

                Q(customer__phone__icontains=keyword) |

                Q(customer__card_number__icontains=keyword)

            )

        return queryset.order_by("-id")


class ServiceExportAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        queryset = Service.objects.select_related(
            "customer",
            "engineer",
            "ro_asset",
        ).order_by("-id")

        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "Service Report"

        headers = [
            "ID",
            "Service ID",
            "Customer",
            "Customer Phone",
            "Engineer",
            "Asset",
            "Service Type",
            "Status",
            "Scheduled Date",
            "Completed Date",
            "Next Service Date",
            "Input TDS",
            "Output TDS",
            "Remarks",
            "Latitude",
            "Longitude",
        ]
        worksheet.append(headers)

        for service in queryset:
            worksheet.append([
                service.id,
                service.service_id,
                service.customer.name if service.customer else "",
                service.customer.phone if service.customer else "",
                service.engineer.name if service.engineer else "",
                service.ro_asset.name if service.ro_asset else "",
                service.service_type,
                service.status,
                service.scheduled_date.isoformat() if service.scheduled_date else "",
                service.completed_date.isoformat() if service.completed_date else "",
                service.next_service_date.isoformat() if service.next_service_date else "",
                service.input_tds or "",
                service.output_tds or "",
                service.remarks or "",
                service.latitude or "",
                service.longitude or "",
            ])

        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="service_report.xlsx"'
        return response


