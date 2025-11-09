from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import Q
from django.utils import timezone


from .models import PricingRule, Cart, CartItem


class PricingService:
    """
    Service layer for discount calculation — **read-only, no database persistence by default**.
    Except: record_applied_rules method

    Purpose:
    - Centralizes all discount computation logic in one place.
    - Does NOT rely on PricingRuleUsage for tracking.
    - Suitable for calculating applicable discounts for a cart without side effects.
    """

    @staticmethod
    def get_applicable_rules(
        cart: Cart, coupon_codes: Optional[List[str]] = None
    ) -> List[PricingRule]:
        """
        Retrieves applicable pricing rules for the cart.
        - Explicit rules (via M2M) first
        - Then automatic rules (coupon or auto_apply=True)
        - Supports min/max cart value for tiered discounts
        - Avoids duplicates
        """
        user = cart.user
        coupon_codes = [c.strip().upper() for c in (coupon_codes or [])]
        now = timezone.now()
        cart_total = cart.subtotal()

        # 1) Explicit rules attached to cart (via M2M)
        explicit_qs = cart.pricing_rules.all()
        explicit_valid: List[PricingRule] = []
        for rule in explicit_qs:
            if not rule.is_active_now(user=user):
                continue
            if rule.currency and rule.currency != cart.currency.code:
                continue
            if rule.max_global_uses and rule.usage_count >= rule.max_global_uses:
                continue
            if rule.per_user_limit and user and user.is_authenticated:
                user_uses = (
                    rule.user_usage.get(str(user.id), 0) if rule.user_usage else 0
                )
                if user_uses >= rule.per_user_limit:
                    continue
            if rule.min_cart_value and cart_total < rule.min_cart_value:
                continue
            if rule.max_cart_value and cart_total > rule.max_cart_value:  # جدید
                continue
            if rule.category and rule.min_category_value:
                cat_total = sum(
                    item.subtotal()
                    for item in cart.items.all()
                    if item.variant.product.category_id == rule.category_id
                )
                if cat_total < rule.min_category_value:
                    continue
            explicit_valid.append(rule)

        explicit_ids: Set[str] = {str(r.id) for r in explicit_valid}

        # 2) Automatic / coupon-based rules
        base_q = (
            Q(active=True)
            & (Q(starts_at__lte=now) | Q(starts_at__isnull=True))
            & (Q(ends_at__gte=now) | Q(ends_at__isnull=True))
            & (Q(currency__isnull=True) | Q(currency=cart.currency.code))
            & (Q(user__isnull=True) | Q(user=user))
            & (
                Q(coupon_code__in=coupon_codes)
                | (Q(coupon_code__isnull=True) & Q(auto_apply=True))
            )
        )
        auto_rules = list(
            PricingRule.objects.filter(base_q).order_by("-priority", "created_at")
        )

        auto_valid: List[PricingRule] = []
        for rule in auto_rules:
            if str(rule.id) in explicit_ids:
                continue
            if not rule.is_active_now(user=user):
                continue
            if rule.max_global_uses and rule.usage_count >= rule.max_global_uses:
                continue
            if rule.per_user_limit and user and user.is_authenticated:
                user_uses = (
                    rule.user_usage.get(str(user.id), 0) if rule.user_usage else 0
                )
                if user_uses >= rule.per_user_limit:
                    continue
            if rule.min_cart_value and cart_total < rule.min_cart_value:
                continue
            if rule.max_cart_value and cart_total > rule.max_cart_value:  # جدید
                continue
            if rule.category and rule.min_category_value:
                cat_total = sum(
                    item.subtotal()
                    for item in cart.items.all()
                    if item.variant.product.category_id == rule.category_id
                )
                if cat_total < rule.min_category_value:
                    continue
            auto_valid.append(rule)

        # 3) Final result: explicit (priority) + automatic
        return explicit_valid + auto_valid

    @staticmethod
    def calculate_discounts(
        cart: Cart, coupon_codes: Optional[List[str]] = None
    ) -> Tuple[Decimal, List[Dict]]:
        """
        Calculates total discount and the list of applied rules for a cart.

        Purpose:
        - Provides a unified way to compute discounts for both stackable and non-stackable rules.
        - Separates computation from database persistence for flexibility.

        Args:
            cart: Cart object containing items to be discounted.
            coupon_codes: Optional list of coupon codes applied by the user.

        Returns:
            Tuple containing:
                total_discount: Decimal, total discount applied.
                applied_rules: List of dicts, each representing an applied rule:
                    {
                        "rule": PricingRule,
                        "discount": Decimal,
                        "applied_to": "cart" | "category" | "item"
                    }
        """
        rules = PricingService.get_applicable_rules(cart, coupon_codes)
        cart_items = list(cart.items.select_related("variant__product").all())
        total_cart = cart.subtotal()
        total_discount = Decimal("0.00")
        applied_rules = []

        # Separate stackable and non-stackable rules
        non_stackable = [r for r in rules if not r.combinable]
        stackable = [r for r in rules if r.combinable]

        # --- Apply the best non-stackable rule ---
        if non_stackable:
            best_rule, best_discount = None, Decimal("0")
            for rule in non_stackable:
                discount = PricingService._compute_discount(
                    rule, cart_items, total_cart
                )
                if discount > best_discount:
                    best_discount, best_rule = discount, rule
            if best_rule:
                total_discount += best_discount
                applied_rules.append(
                    {
                        "rule": best_rule,
                        "discount": best_discount,
                        "applied_to": PricingService._get_applied_to(best_rule),
                    }
                )

        # --- Apply all stackable rules ---
        for rule in stackable:
            discount = PricingService._compute_discount(rule, cart_items, total_cart)
            if discount > 0:
                total_discount += discount
                applied_rules.append(
                    {
                        "rule": rule,
                        "discount": discount,
                        "applied_to": PricingService._get_applied_to(rule),
                    }
                )

        return total_discount, applied_rules

    @staticmethod
    def _get_applied_to(rule: PricingRule) -> str:
        """
        Determines the scope of the pricing rule.

        Returns:
            str: One of "cart", "category", "item", or "unknown".
        """
        if rule.rule_type.startswith("cart_"):
            return "cart"
        elif rule.rule_type.startswith("category_"):
            return "category"
        elif rule.rule_type.startswith("product_"):
            return "item"
        return "unknown"

    @staticmethod
    def _compute_discount(
        rule: PricingRule, cart_items: List[CartItem], total_cart: Decimal
    ) -> Decimal:
        """
        Computes the discount amount for a given rule and cart items.

        Purpose:
        - Encapsulates the logic of calculating a single rule’s effect.
        - Handles different scopes: cart, category, or product.

        Args:
            rule: PricingRule to apply.
            cart_items: List of CartItem objects.
            total_cart: Total cart value before discounts.

        Returns:
            Decimal: Discount amount for this rule, quantized to two decimal places.
        """
        # Determine base amount
        if rule.rule_type.startswith("cart_"):
            base = total_cart
        elif rule.rule_type.startswith("category_") and rule.category:
            base = sum(
                item.subtotal()
                for item in cart_items
                if item.variant.product.category_id == rule.category_id
            )
        elif rule.rule_type.startswith("product_"):
            # Assumes rule.category_id represents product_id for product-specific rules
            base = sum(
                item.subtotal()
                for item in cart_items
                if item.variant.product.id == rule.category_id
            )
        else:
            return Decimal("0")

        if base <= 0:
            return Decimal("0")

        # Calculate discount
        if "percentage" in rule.rule_type and rule.discount_percentage:
            discount = base * (rule.discount_percentage / Decimal("100"))
        elif rule.discount_amount:
            discount = min(rule.discount_amount, base)
        else:
            return Decimal("0")

        # Apply maximum discount cap
        if rule.max_discount_amount:
            discount = min(discount, rule.max_discount_amount)

        return discount.quantize(Decimal("0.01"))

    @staticmethod
    def record_applied_rules(cart: Cart, applied_rules: List[Dict]):
        """
        Should be called after the order is finalized:
        - Increments `usage_count` and `user_usage` in PricingRule.
        - If a rule is not yet attached to the cart, link it through M2M.
        - If a through model is used (e.g., CartAppliedRule),
        you can create a record there to store the discount value.
        """
        if not applied_rules:
            return

        user = cart.user
        user_id = str(user.id) if user and user.is_authenticated else None

        with transaction.atomic():
            for item in applied_rules:
                rule: PricingRule = item["rule"]
                discount: Decimal = item.get("discount") or Decimal("0.00")

                # Increment total usage count
                rule.usage_count = (rule.usage_count or 0) + 1

                # Increment per-user usage counter (stored in JSONField)
                if user_id and rule.per_user_limit:
                    user_usage = rule.user_usage or {}
                    user_usage[user_id] = user_usage.get(user_id, 0) + 1
                    rule.user_usage = user_usage

                # Save updated usage data
                rule.save(update_fields=["usage_count", "user_usage"])

                # If the rule is not yet linked to this cart, attach it via M2M.
                # This ensures a historical record of which rules were applied to this cart.
                if not cart.pricing_rules.filter(pk=rule.pk).exists():
                    cart.pricing_rules.add(rule)

                # If a through model is used (e.g., CartAppliedRule),
                # you can create a record to store details like the applied discount.
                # Example:
                # CartAppliedRule.objects.create(cart=cart, rule=rule, discount_value=discount)
