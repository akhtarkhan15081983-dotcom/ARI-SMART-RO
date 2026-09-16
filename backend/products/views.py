from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.generics import get_object_or_404

from accounts.permissions import IsReadOnlyOrStaffOperator
from django.db.models import Q
from .models import (
    ProductCategory,
    ROModel,
    ROModelPart,
    ROModelImage,
)

from .serializers import (
    ProductCategorySerializer,
    ROModelSerializer,
    ROModelPartSerializer,
)


class ProductCategoryAPIView(APIView):

    permission_classes = [IsReadOnlyOrStaffOperator]

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

    permission_classes = [IsReadOnlyOrStaffOperator]

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


class ROModelDetailAPIView(APIView):
    permission_classes = [IsReadOnlyOrStaffOperator]

    def patch(self, request, model_id):
        product = get_object_or_404(ROModel, id=model_id)
        serializer = ROModelSerializer(
            product,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, model_id):
        product = get_object_or_404(ROModel, id=model_id)
        product.is_active = False
        product.save(update_fields=["is_active"])
        return Response({"success": True, "message": "Product deactivated."})


class ROModelImageAPIView(APIView):
    permission_classes = [IsReadOnlyOrStaffOperator]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, model_id):
        product = get_object_or_404(ROModel, id=model_id)
        image = request.FILES.get("image")
        if image is None:
            return Response({"image": ["Product image is required."]}, status=400)
        if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            return Response({"image": ["Use a JPEG, PNG or WebP image."]}, status=400)
        if image.size > 8 * 1024 * 1024:
            return Response({"image": ["Image must be 8 MB or smaller."]}, status=400)
        product.images.all().delete()
        ROModelImage.objects.create(
            ro_model=product,
            image=image,
            alt_text=product.model_name,
        )
        serializer = ROModelSerializer(
            product,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ROModelPartAPIView(APIView):

    permission_classes = [IsReadOnlyOrStaffOperator]

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


class CustomerShopCatalogAPIView(APIView):
    """Public read-only catalog used by the guest and customer storefront."""

    permission_classes = [AllowAny]

    def get(self, request):
        keyword = request.GET.get("q", "").strip()
        category_id = request.GET.get("category", "").strip()

        queryset = ROModel.objects.select_related("category").prefetch_related("images").filter(
            Q(available_for_sale=True, selling_price__gt=0)
            | Q(available_for_rent=True, monthly_rent__gt=0),
            is_active=True,
            category__is_active=True,
        )

        if keyword:
            queryset = queryset.filter(
                Q(model_name__icontains=keyword)
                | Q(category__name__icontains=keyword)
                | Q(capacity__icontains=keyword)
            )

        if category_id.isdigit():
            queryset = queryset.filter(category_id=int(category_id))

        serializer = ROModelSerializer(
            queryset.order_by("category__name", "model_name"),
            many=True,
            context={"request": request},
        )

        return Response({"products": serializer.data})
