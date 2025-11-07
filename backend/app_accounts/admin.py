from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Profile, Vendor, Follow


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"
    fk_name = "user"
    extra = 1


class VendorInline(admin.StackedInline):
    model = Vendor
    can_delete = True
    verbose_name_plural = "Vendor"
    fk_name = "user"
    extra = 1


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline, VendorInline]
    list_display = ("email", "is_vendor", "is_customer", "is_staff", "is_active")
    list_filter = ("is_vendor", "is_customer", "is_staff", "is_active")
    search_fields = ("email",)
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Roles", {"fields": ("is_vendor", "is_customer")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_vendor",
                    "is_customer",
                ),
            },
        ),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone_number", "address")
    search_fields = ("user__email", "phone_number")
    list_select_related = ("user",)


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("shop_name", "user", "description")
    search_fields = ("shop_name", "user__email")
    list_filter = ("followers",)
    filter_horizontal = ("followers",)
    list_select_related = ("user",)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("user", "vendor", "created_at")
    search_fields = ("user__email", "vendor__shop_name")
    list_select_related = ("user", "vendor")
