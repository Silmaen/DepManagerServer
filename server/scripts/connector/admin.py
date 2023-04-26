"""Fichier admin.py exemple de profil user"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    """Definition d’un descripteur inline pour le model profil."""
    model = UserProfile
    can_delete = False
    verbose_name = 'Utilisateur'
    verbose_name_plural = 'Utilisateurs'


class UserAdmin(BaseUserAdmin):
    """Définition d’un nouveau User Admin."""
    inlines = (UserProfileInline,)


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

