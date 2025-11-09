import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from app_products.models import Category, Currency, Product, ProductVariant

User = get_user_model()


class Cart(models.Model):
    """
    Represents a shopping cart.
    Can be associated with a user or an anonymous session (via session_key).
    Supports multiple currencies and vendors.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="carts",
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=255, blank=True, null=True)
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="carts",
        help_text="Currency in which this cart operates (matches product variant currency).",
    )
    # pricing_rule = models.ForeignKey(
    #     "PricingRule",
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name="carts",
    #     help_text="Applied discount or pricing rule, if any.",
    # )
    pricing_rules = models.ManyToManyField(
        "PricingRule",
        blank=True,
        related_name="carts",
        help_text="All applied pricing rules or coupons for this cart.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        user_display = self.user.email if self.user else self.session_key or "Guest"
        return f"Cart ({user_display}) [{self.currency}]"

    def subtotal(self):
        """Sum of all item prices before discounts."""
        return sum(item.subtotal() for item in self.items.all())

    def total_items(self):
        """Total quantity of items in cart."""
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """
    Represents an item in a shopping cart.
    Each item corresponds to one ProductVariant.
    """

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "variant")

    def __str__(self):
        return f"{self.variant.product.name} × {self.quantity}"

    def clean(self):
        """Ensure cart currency matches variant currency."""
        if self.cart.currency != self.variant.currency:
            raise ValidationError("Variant currency does not match cart currency.")

    def subtotal(self):
        """Price before any cart-level discount."""
        return self.variant.price * self.quantity

    def get_total_price_display(self):
        """Human-readable total with currency."""
        return f"{self.subtotal()} {self.cart.currency.code}"


class PricingRule(models.Model):
    """
    Represents a dynamic pricing or discount rule that can apply to
    products, categories, or entire carts.

    This model is designed to handle flexible discounting strategies
    similar to systems used in advanced e-commerce platforms.

    Each rule defines:
    - **Type** (cart-level, category-level, product-level)
    - **Discount style** (percentage or fixed)
    - **Optional constraints** such as minimum cart value, usage limits,
      or start/end validity periods.
    - **Combination behavior** (whether it can be combined with other rules)
    - **Priority order** (when multiple rules apply)

    Example use cases:
    -------------------
    1️ **Cart-wide percentage discount**
        → "10% off for orders above $100"
        >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        rule_type = "cart_percentage"
        discount_percentage = 10
        min_cart_value = 100
        >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    2️ **Category-specific fixed discount**
        → "$5 off all Electronics over $50"
        >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        rule_type = "category_fixed"
        discount_amount = 5
        category = Category(name="Electronics")
        min_category_value = 50
        >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    3️ **Coupon-based product discount**
        → "20% off product XYZ with code SAVE20"
        >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        rule_type = "product_percentage"
        discount_percentage = 20
        code = "SAVE20"
        >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    4️ **Limited-time cart promotion**
        → "Black Friday 30% off entire cart between Nov 25–27"
        >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        rule_type = "cart_percentage"
        discount_percentage = 30
        starts_at = "2025-11-25T00:00"
        ends_at = "2025-11-27T23:59"
        >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    The `is_active_now()` method helps validate if a rule is currently
    active and eligible for application.
    """

    RULE_TYPE_CHOICES = [
        ("cart_percentage", "Cart - Percentage"),
        ("cart_fixed", "Cart - Fixed amount"),
        ("category_percentage", "Category - Percentage"),
        ("category_fixed", "Category - Fixed amount"),
        ("product_percentage", "Product - Percentage"),
        ("product_fixed", "Product - Fixed amount"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=255,
        help_text="Name of the pricing rule (e.g. 'Black Friday 10% off').",
    )
    description = models.TextField(
        blank=True, help_text="Optional description or notes for internal reference."
    )

    # Conditions
    min_cart_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum total cart value required for this rule to apply (optional).",
    )
    max_cart_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum cart value for this rule to apply (optional). For tiered discounts.",
    )
    min_category_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum total category value required if this rule targets a specific category (optional).",
    )

    rule_type = models.CharField(
        max_length=32,
        choices=RULE_TYPE_CHOICES,
        help_text="Defines how the rule applies (cart-level, category-level, or product-level).",
    )

    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Discount percentage (0–100). Used for percentage-based rules.",
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Fixed discount amount (e.g., $10 off). Used for fixed-value rules.",
    )

    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="If the rule applies to a specific category, set it here.",
    )

    coupon_code = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        unique=True,
        help_text="Coupon code for manual application. Leave blank for automatic rules.",
    )

    # Scheduling
    starts_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when this rule becomes active (optional).",
    )
    ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when this rule expires (optional).",
    )

    # Limits and usage
    active = models.BooleanField(
        default=True, help_text="Determines whether the rule is currently enabled."
    )
    max_global_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum total number of times this rule can be used across all users.",
    )
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text="Tracks how many times this rule has been used (auto-updated on each usage).",
    )
    per_user_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum times a single user can use this rule (null = unlimited).",
    )
    user_usage = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-user usage tracking: {'user_id': count}",
    )
    combinable = models.BooleanField(
        default=False,
        help_text="If True, this rule can be combined with other discounts in the same cart.",
    )

    priority = models.IntegerField(
        default=0,
        db_index=True,
        help_text="Higher values indicate higher priority when multiple rules are active.",
    )

    max_discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum discount amount this rule can apply (optional).",
    )

    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_pricing_rules",
        help_text="User who created this rule (optional).",
    )
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="assigned_pricing_rules",
        help_text="It will only apply to a specific customer",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when this rule was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp of the last modification to this rule."
    )
    currency = models.CharField(
        max_length=3,
        choices=[
            ("USD", "US Dollar"),
            ("EUR", "Euro"),
            ("GBP", "Pound"),
            ("IRR", "Iranian Rial"),
        ],
        null=True,
        blank=True,
        help_text="If be empty for all pricing rule will applied on each currency.",
    )
    auto_apply = models.BooleanField(
        default=False, help_text="Apply automatically if no coupon code is provided."
    )

    class Meta:
        ordering = ["-priority", "starts_at"]
        verbose_name = "Pricing Rule"
        verbose_name_plural = "Pricing Rules"

    def __str__(self):
        return f"{self.name} - ({self.rule_type})"

    def save(self, *args, **kwargs):
        if self.coupon_code:
            self.coupon_code = self.coupon_code.strip().upper()
        if self.name:
            self.name = self.name.strip().upper()
        super().save(*args, **kwargs)

    def is_active_now(self, user=None):
        """
        Returns True if this pricing rule is currently active
        based on its `active` flag, start/end times, and usage limits.
        """
        now = timezone.now()
        if not self.active:
            return False
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        if (
            self.max_global_uses is not None
            and self.usage_count >= self.max_global_uses
        ):
            return False
        if self.user and user is not None and self.user != user:
            return False
        return True
