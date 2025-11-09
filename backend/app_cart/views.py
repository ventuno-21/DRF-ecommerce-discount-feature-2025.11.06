from decimal import Decimal

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from app_products.models import Product, ProductVariant

from .models import Cart, CartItem
from .serializers import CartPreviewSerializer
from .services import PricingService


class CartPreviewAPIView(APIView):
    """
    API view to preview a shopping cart and calculate discounts.

    Purpose:
    - Provides a temporary cart preview without persisting active orders.
    - Calculates discounts using the PricingService.
    - Returns subtotal, total discounts, applied rules, and item details.
    """

    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    serializer_class = CartPreviewSerializer

    def post(self, request):
        """
        Handle POST requests to preview a cart.

        Expected request data:
        {
            "items": [
                {"product_id": int, "variant_id": int, "quantity": int},  # variant_id optional
                ...
            ],
            "coupon_codes": ["CODE1", "CODE2"]
        }

        Returns:
            JSON response with:
            - subtotal, total_discount, total
            - applied pricing rules
            - detailed cart items
        """
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        items_data = serializer.validated_data["items"]
        coupon_codes = serializer.validated_data.get("coupon_codes", [])

        # Optional user
        user = request.user if request.user.is_authenticated else None

        # Create temporary cart in database
        cart = self._create_temp_cart(user, items_data)
        if not cart:
            return Response(
                {
                    "error": "Unable to create cart preview. Check variant availability or stock."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Calculate discounts using PricingService
        total_discount, applied_rules = PricingService.calculate_discounts(
            cart, coupon_codes
        )

        # Calculate final totals
        subtotal = cart.subtotal()
        total = subtotal - total_discount

        # Prepare response data
        response_data = {
            "subtotal": f"{subtotal:.2f}",
            "total_discount": f"{total_discount:.2f}",
            "total": f"{total:.2f}",
            "currency": cart.currency.code,
            "applied_rules": [
                {
                    "name": rule["rule"].name,
                    "discount": f"{rule['discount']:.2f}",
                    "applied_to": rule["applied_to"],
                    "type": rule["rule"].get_rule_type_display(),
                }
                for rule in applied_rules
            ],
            "items": [
                {
                    "product_id": item.variant.product.id,
                    "variant_id": item.variant.id,
                    "name": item.variant.product.name,
                    "variant_sku": item.variant.sku,
                    "quantity": item.quantity,
                    "price": f"{item.variant.price:.2f}",
                    "subtotal": f"{item.subtotal():.2f}",
                }
                for item in cart.items.all()
            ],
        }

        return Response(response_data, status=status.HTTP_200_OK)

    @transaction.atomic
    def _create_temp_cart(self, user, items_data):
        """
        Creates a temporary cart in the database using:
        - variant_id if provided
        - first active variant of the product otherwise

        Purpose:
        - Used only for preview and discount calculation.
        - Cart is marked inactive and will be cleaned up later if needed.
        - Returns None on failure (invalid variant, stock, etc.)

        Args:
            user: Optional authenticated user.
            items_data: List of validated item dicts with product_id/variant_id/quantity.

        Returns:
            Cart instance or None.
        """
        if not items_data:
            return None

        # Determine currency from first valid variant
        first_variant = self._get_variant_from_item(items_data[0])
        if not first_variant:
            return None

        # Create temporary cart
        cart = Cart.objects.create(
            user=user,
            session_key=None,
            currency=first_variant.currency,
            is_active=False,  # Mark as preview-only
        )

        # Add all items
        for item_data in items_data:
            variant = self._get_variant_from_item(item_data)
            if not variant:
                cart.delete()
                return None

            # Ensure all items use the same currency
            if variant.currency != cart.currency:
                cart.delete()
                return None

            # Check stock
            if variant.stock < item_data["quantity"]:
                cart.delete()
                return None

            CartItem.objects.create(
                cart=cart, variant=variant, quantity=item_data["quantity"]
            )

        return cart

    def _get_variant_from_item(self, item_data):
        """
        Helper to resolve variant:
        - Use variant_id if provided
        - Otherwise, use first active variant of the product
        """
        variant_id = item_data.get("variant_id")
        product_id = item_data.get("product_id")

        if variant_id:
            try:
                return ProductVariant.objects.get(id=variant_id, is_active=True)
            except ProductVariant.DoesNotExist:
                return None

        if product_id:
            return ProductVariant.objects.filter(
                product_id=product_id, is_active=True
            ).first()

        return None
