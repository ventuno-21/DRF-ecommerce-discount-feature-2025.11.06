from rest_framework import serializers
from .models import (
    Product,
    Brand,
    Category,
    Attribute,
    AttributeValue,
    ProductVariant,
    ProductImage,
    ProductVariantImage,
    Currency,
)
from app_accounts.models import Vendor


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "slug"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent"]


class AttributeValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeValue
        fields = ["id", "attribute", "value"]


class AttributeSerializer(serializers.ModelSerializer):
    values = AttributeValueSerializer(many=True, read_only=True)

    class Meta:
        model = Attribute
        fields = ["id", "name", "slug", "values"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "is_main", "created_at"]


class ProductVariantImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariantImage
        fields = ["id", "image", "alt_text", "is_main", "created_at"]


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["id", "code", "name", "symbol"]


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ["id", "shop_name"]


class ProductVariantSerializer(serializers.ModelSerializer):
    attributes = AttributeValueSerializer(many=True)
    vendor = VendorSerializer(read_only=True)
    vendor_id = serializers.PrimaryKeyRelatedField(
        queryset=Vendor.objects.all(), source="vendor", write_only=True
    )
    currency = CurrencySerializer(read_only=True)
    currency_id = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.all(), source="currency", write_only=True
    )
    images = ProductVariantImageSerializer(many=True, read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "product",
            "vendor",
            "vendor_id",
            "currency",
            "currency_id",
            "attributes",
            "sku",
            "price",
            "stock",
            "image",
            "is_active",
            "created_at",
            "images",
        ]
        read_only_fields = ["sku", "created_at"]

    def validate_attributes(self, value):
        if not value:
            raise serializers.ValidationError("At least one attribute is required.")
        return value

    def create(self, validated_data):
        attributes_data = validated_data.pop("attributes")
        variant = ProductVariant.objects.create(**validated_data)
        variant.attributes.set(attributes_data)
        variant.save()  # triggers SKU generation and clean()
        return variant

    def update(self, instance, validated_data):
        attributes_data = validated_data.pop("attributes", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if attributes_data is not None:
            instance.attributes.set(attributes_data)
        instance.save()  # triggers clean() and SKU update
        return instance


class ProductSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(),
        source="brand",
        write_only=True,
        required=False,
        allow_null=True,
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "brand",
            "brand_id",
            "category",
            "category_id",
            "description",
            "main_image",
            "created_at",
            "images",
            "variants",
        ]
        read_only_fields = ["slug", "created_at"]

    def create(self, validated_data):
        return Product.objects.create(**validated_data)
