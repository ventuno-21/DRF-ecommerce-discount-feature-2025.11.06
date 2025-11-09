from django.contrib import admin
from .models import (
    Brand,
    Category,
    Currency,
    Product,
    Attribute,
    AttributeValue,
    ProductVariant,
    ProductImage,
    ProductVariantImage,
    VendorProduct,
)
from app_accounts.models import Vendor


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "slug")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("parent",)
    search_fields = ("name",)


class AttributeValueInline(admin.TabularInline):
    model = AttributeValue
    extra = 1
    fields = ("value",)
    show_change_link = True


@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    list_display = ("attribute", "value")
    list_filter = ("attribute",)
    search_fields = ("value",)


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    inlines = [AttributeValueInline]  # ← AttributeValue as inline


class ProductVariantImageInline(admin.TabularInline):
    model = ProductVariantImage
    extra = 1
    fields = ("image",)
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" width="50" />'
        return "-"

    image_preview.allow_tags = True
    image_preview.short_description = "Preview"


class ProductVariantVendorInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("vendor", "price", "stock", "sku", "is_active")
    readonly_fields = ("sku",)
    autocomplete_fields = ("vendor",)
    show_change_link = True


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = (
        "vendor",
        "price",
        "stock",
        "attributes",
        "sku",
        "is_active",
        "currency",
    )
    readonly_fields = ("sku",)
    autocomplete_fields = ("vendor", "attributes")
    show_change_link = True


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image",)
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" width="50" />'
        return "-"

    image_preview.allow_tags = True
    image_preview.short_description = "Preview"


class VendorProductInline(admin.TabularInline):
    model = VendorProduct
    extra = 1
    fields = ("vendor", "variant", "price", "stock", "is_active")
    autocomplete_fields = ("vendor", "variant")
    show_change_link = True


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "brand",
        "category",
        "created_at",
        # "get_currencies",
    )
    search_fields = ("name", "brand__name", "category__name")
    list_filter = ("brand", "category")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductVariantInline, ProductImageInline]

    # def get_currencies(self, obj):
    #     currencies = obj.variants.values_list(
    #         "vendor_offers__currency__code", flat=True
    #     ).distinct()
    #     return ", ".join([c for c in currencies if c]) or "—"

    # get_currencies.short_description = "Currencies"


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "vendor",
        "price",
        "stock",
        "sku",
        "is_active",
        "created_at",
    )
    list_filter = ("vendor", "is_active")
    search_fields = ("product__name", "vendor__shop_name", "sku")
    autocomplete_fields = ("product", "vendor", "attributes")
    readonly_fields = ("sku",)
    inlines = [ProductVariantImageInline, VendorProductInline]


class VendorProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("product", "price", "stock", "sku", "is_active")
    readonly_fields = ("sku",)
    autocomplete_fields = ("product", "attributes")
    show_change_link = True
    inlines = [ProductVariantImageInline]


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "symbol", "exchange_rate", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
