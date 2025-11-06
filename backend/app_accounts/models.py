from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


# Custom User Manager
class CustomUserManager(BaseUserManager):
    """
    Custom manager for the User model where authentication is done via email instead of username.

    This manager overrides the default Django UserManager to ensure that:
    - Users are created with an email as the unique identifier.
    - Passwords are properly hashed using `set_password()`.
    - Superusers are created with the correct permissions (`is_staff=True`, `is_superuser=True`).

    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email should be enterned!")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email


def user_profile_upload_path(instance, filename):
    return f"profile_pics/user_{instance.user.id}/{filename}"


def shop_image_upload_path(instance, filename):
    return f"profile_pics/vendor_{instance.user.id}/{filename}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    address = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    image = models.ImageField(
        upload_to=user_profile_upload_path, default="profile_pics/0_default_profile.jpg"
    )

    def __str__(self):
        return {self.user.email}


class Vendor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    shop_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    logo = models.ImageField(
        upload_to=shop_image_upload_path, default="vendor_logos/0_default_shop.jpg"
    )
    followers = models.ManyToManyField(
        User, related_name="following_vendors", blank=True
    )

    def __str__(self):
        return self.shop_name


class Follow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vendor = models.ForeignKey("Vendor", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "vendor")

    def __str__(self):
        return f"{self.user.email} follows {self.vendor.shop_name}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
