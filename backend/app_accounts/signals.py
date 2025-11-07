from django.db.models.signals import post_save
from django.dispatch import receiver

from app_accounts.models import Profile, User, Vendor


# @receiver(post_save, sender=User)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         Profile.objects.create(user=instance)


def create_profile_and_vendor(sender, instance, created, **kwargs):
    # همیشه پروفایل بساز:
    if created:
        Profile.objects.create(user=instance)

    # اگر user.is_vendor و vendor موجود نیست => بساز
    if instance.is_vendor:
        Vendor.objects.get_or_create(
            user=instance,
            defaults={"shop_name": f"{instance.email.split('@')[0]}-shop"},
        )
