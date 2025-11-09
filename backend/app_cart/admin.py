from django.contrib import admin
from .models import Cart, CartItem, PricingRule


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1
    autocomplete_fields = ["variant"]
    readonly_fields = ["added_at"]
    show_change_link = True


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "currency", "created_at", "is_active"]
    list_filter = ["currency", "is_active", "created_at"]
    search_fields = ["user__email", "session_key"]
    inlines = [CartItemInline]
    autocomplete_fields = ["user", "currency", "pricing_rules"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "session_key",
                    "currency",
                    "pricing_rules",
                    "is_active",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(PricingRule)
class PricingRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "rule_type", "active", "priority", "usage_count"]
    list_filter = ["active", "rule_type", "starts_at", "ends_at", "currency"]
    search_fields = ["name", "coupon_code", "description"]
    autocomplete_fields = ["category", "user", "created_by"]
    readonly_fields = ["usage_count", "created_at", "updated_at"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "description",
                    "rule_type",
                    "discount_percentage",
                    "discount_amount",
                    "category",
                    "coupon_code",
                    "currency",
                    "min_cart_value",
                    "max_cart_value",
                    "active",
                )
            },
        ),
        (
            "Limits",
            {
                "fields": (
                    "max_global_uses",
                    "usage_count",
                    "per_user_limit",
                    "user_usage",
                    "max_discount_amount",
                )
            },
        ),
        ("Schedule", {"fields": ("starts_at", "ends_at")}),
        ("Ownership", {"fields": ("user", "created_by")}),
        ("Meta", {"fields": ("priority", "combinable", "created_at", "updated_at")}),
    )
