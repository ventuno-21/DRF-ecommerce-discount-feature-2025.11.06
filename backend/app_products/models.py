import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from app_accounts.models import Vendor


def product_main_image_upload_path(instance, filename):
    return f"products/main/pdc_{instance.id}/{filename}"


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name = "Brand"
        verbose_name_plural = "Brands"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Represents a base product (e.g., Samsung Galaxy S24).
    Each product can have multiple variants (color, size, RAM, Material, etc.)
    and can be sold by multiple vendors.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    description = models.TextField(blank=True)
    main_image = models.ImageField(
        upload_to=product_main_image_upload_path,
        default="products/main/0_default_product.jpg",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Attribute(models.Model):
    """
    Defines an attribute type such as "Color", "Size", "RAM", "Material" & ....
    """

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class AttributeValue(models.Model):
    """
    Defines possible values for an attribute
    (e.g., "Red" for Color, "128GB" for RAM, "40" for Size).
    """

    attribute = models.ForeignKey(
        Attribute, on_delete=models.CASCADE, related_name="values"
    )
    value = models.CharField(max_length=50)

    # class Meta:
    #     unique_together = ("attribute", "value")

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/gallery/")
    alt_text = models.CharField(max_length=255, blank=True)
    is_main = models.BooleanField(default=False)  # main image flag
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_main", "id"]

    def __str__(self):
        return f"{self.product.name} - {self.alt_text or 'Image'}"


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    vendor = models.ForeignKey(
        Vendor, on_delete=models.CASCADE, related_name="variants"
    )
    attributes = models.ManyToManyField(AttributeValue, related_name="variants")
    sku = models.CharField(max_length=100, unique=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to="products/variants/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        """
            Validates that there are no duplicate ProductVariant entries
        for the same product, vendor, and combination of attributes.

        Raises:
            ValidationError: If another variant with the same product,
            vendor, and attributes already exists.
        """
        if not self.pk or not self.product_id or not self.vendor_id:
            return
        if self.pk:
            existing_variants = ProductVariant.objects.exclude(pk=self.pk)
        else:
            existing_variants = ProductVariant.objects.all()

        for variant in existing_variants.filter(
            product=self.product, vendor=self.vendor
        ):
            existing_attrs = set(variant.attributes.values_list("id", flat=True))
            new_attrs = set(self.attributes.values_list("id", flat=True))
            if existing_attrs == new_attrs:
                raise ValidationError(
                    "This combination of product, vendor, and attributes already exists."
                )

    def save(self, *args, **kwargs):
        if not self.pk and not self.sku:
            super().save(*args, **kwargs)  # temporary save to get PK

        attr_codes = "-".join(
            [slugify(a.value)[:3].upper() for a in self.attributes.all()]
        )
        product_code = slugify(self.product.name)[:5].upper()
        self.sku = f"{product_code}-{attr_codes}-{self.vendor.id}"

        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        attrs_text = ", ".join([str(a) for a in self.attributes.all()])
        return f"{self.product.name} ({self.vendor.shop_name}) [{attrs_text}]"

    def attributes_text(self):
        return ", ".join([str(a) for a in self.attributes.all()])

    def get_main_image(self):
        """
        Returns the main image for this variant.
        Fallback to product's main image if variant has no image.
        """
        main_image = self.images.filter(is_main=True).first()
        if main_image:
            return main_image.image.url
        elif self.images.exists():
            return self.images.first().image.url
        elif self.product.images.filter(is_main=True).exists():
            return self.product.images.filter(is_main=True).first().image.url
        elif self.product.images.exists():
            return self.product.images.first().image.url
        else:
            return None  # placeholder


class ProductVariantImage(models.Model):
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/variants/")
    alt_text = models.CharField(max_length=255, blank=True)
    is_main = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_main", "id"]

    def __str__(self):
        return f"{self.variant} - {self.alt_text or 'Image'}"


class VendorProduct(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="offers")
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="vendor_offers"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    sku = models.CharField(max_length=100, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("vendor", "variant")

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f"{self.variant.sku}-{self.vendor.id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vendor.shop_name} - {self.variant} @ {self.price}$"
