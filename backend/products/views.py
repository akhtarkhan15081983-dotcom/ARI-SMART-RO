from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import (
    ProductCategory,
    ROModel,
    ROModelPart,
)

from .serializers import (
    ProductCategorySerializer,
    ROModelSerializer,
    ROModelPartSerializer,
)


class ProductCategoryAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        queryset = ProductCategory.objects.all().order_by("name")

        serializer = ProductCategorySerializer(
            queryset,
            many=True
        )

        return Response(serializer.data)

    def post(self, request):

        serializer = ProductCategorySerializer(
            data=request.data
        )

        if serializer.is_valid():
            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class ROModelAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        queryset = ROModel.objects.select_related(
            "category"
        ).all().order_by("model_name")

        serializer = ROModelSerializer(
            queryset,
            many=True
        )

        return Response(serializer.data)

    def post(self, request):

        serializer = ROModelSerializer(
            data=request.data
        )

        if serializer.is_valid():
            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class ROModelPartAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        queryset = ROModelPart.objects.select_related(
            "ro_model",
            "part"
        ).all()

        serializer = ROModelPartSerializer(
            queryset,
            many=True
        )

        return Response(serializer.data)

    def post(self, request):

        serializer = ROModelPartSerializer(
            data=request.data
        )

        if serializer.is_valid():
            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )




class ProductSearchAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        keyword = request.GET.get("q", "").strip()

        queryset = ROModel.objects.select_related(
            "category"
        )

        if keyword:

            queryset = queryset.filter(

                Q(model_name__icontains=keyword) |
                Q(category__name__icontains=keyword) |
                Q(capacity__icontains=keyword) |
                Q(business_type__icontains=keyword)

            )

        serializer = ROModelSerializer(
            queryset.order_by("model_name"),
            many=True
        )

        return Response(serializer.data)

