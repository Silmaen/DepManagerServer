"""Fichier main.users.users_view.py les vues users."""
from django.contrib.auth import login
from django.contrib.auth.views import PasswordResetView
from django.shortcuts import render, redirect, reverse

from . import settings
from .forms import CustomUserCreationForm, CustomUserChangeForm


def profile(request):
    """User wants to view its profile."""
    if request.user.is_authenticated:
        return render(request, "registration/profile.html", {
            **settings.base_info, "user": request.user
        })
    else:
        return register(request)


def register(request):
    """Register new user."""
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(reverse("index"))
        return render(request, "registration/register.html", {
            **settings.base_info,
            "form": form
        })
    else:
        return render(request, "registration/register.html", {
            **settings.base_info,
            "form": CustomUserCreationForm
        })


def profile_edit(request):
    """
    User wants to edit its profile.
    """
    if request.method == "POST":
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect(reverse("profile"))
    else:
        form = CustomUserChangeForm(instance=request.user)
    return render(request, "registration/profile_change.html", {
        **settings.base_info,
        "form": form,
    })


class CustomPasswordResetView(PasswordResetView):
    """
    Custom class for password reset.
    """
    from_email = "webmaster@argawaen.net"
    html_email_template_name = 'registration/password_reset_email.html'
