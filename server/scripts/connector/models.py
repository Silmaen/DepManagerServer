"""Fichier UserProfile.models.py pour les modèles d’utilisateurs"""
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Exemple de profile"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    avatar = models.ImageField(blank=True, null=True, verbose_name="avatar", upload_to='user_avatar')
    birthDate = models.DateField(blank=True, null=True, verbose_name="date de naissance")


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Lorsque l’on crée un `User`, cela crée un profil aussi."""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Lorsque l’on sauve un `User` on le fait aussi pour son profil."""
    instance.userprofile.save()
