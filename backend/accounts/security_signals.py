from django.db.models.signals import pre_save
from django.dispatch import receiver
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from .models import User


@receiver(pre_save, sender=User)
def revoke_refresh_tokens_on_password_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    previous = sender.objects.filter(pk=instance.pk).only("password").first()
    if previous is None or previous.password == instance.password:
        return
    for token in OutstandingToken.objects.filter(user_id=instance.pk):
        BlacklistedToken.objects.get_or_create(token=token)
