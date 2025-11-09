from rest_framework import serializers
from app_products.models import Product, ProductVariant


class CartPreviewItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=False)
    variant_id = serializers.IntegerField(required=False)
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, data):
        product_id = data.get("product_id")
        variant_id = data.get("variant_id")

        if not product_id and not variant_id:
            raise serializers.ValidationError(
                "Either 'product_id' or 'variant_id' must be provided."
            )

        if product_id and variant_id:
            if not ProductVariant.objects.filter(
                id=variant_id, product_id=product_id
            ).exists():
                raise serializers.ValidationError(
                    "The variant does not belong to the specified product."
                )

        return data

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError("Product does not exist.")
        return value

    def validate_variant_id(self, value):
        if not ProductVariant.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Variant does not exist or is inactive.")
        return value


class CartPreviewSerializer(serializers.Serializer):
    """
    Main serializer for cart preview API.
    Validates both items and coupon codes.
    """

    items = CartPreviewItemSerializer(many=True)
    coupon_codes = serializers.ListField(
        child=serializers.CharField(max_length=64, allow_blank=True),
        required=False,
        allow_empty=True,
        help_text="List of coupon codes to apply (case-insensitive).",
    )

    def validate_coupon_codes(self, value):
        # remove spaces and convert it to uppercase letters
        return [code.strip().upper() for code in value if code.strip()]
