from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Product, ProductVariant
from .serializers import ProductSerializer, ProductVariantSerializer


class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.select_related("brand", "category").prefetch_related(
        "images", "variants__attributes"
    )
    serializer_class = ProductSerializer
    permission_classes = [
        AllowAny
    ]  # should be change to IsAuthenticated in production-level

    def perform_create(self, serializer):
        serializer.save()


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.select_related("brand", "category").prefetch_related(
        "images", "variants__attributes"
    )
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductVariantListCreateView(generics.ListCreateAPIView):
    queryset = ProductVariant.objects.select_related(
        "product", "vendor", "currency"
    ).prefetch_related("attributes", "images")
    serializer_class = ProductVariantSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        serializer.save()


class ProductVariantDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductVariant.objects.select_related(
        "product", "vendor", "currency"
    ).prefetch_related("attributes", "images")
    serializer_class = ProductVariantSerializer
    permission_classes = [AllowAny]

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
