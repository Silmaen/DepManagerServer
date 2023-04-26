"""Fichier main.urls.py définissant les urls."""
from django.urls import path
from django.contrib.auth.views import *
from .views import *

urlpatterns = [
    path('', profile, name="profile"),

    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    path('password/', PasswordChangeView.as_view(), name="password"),
    path('password/done', PasswordChangeDoneView.as_view(), name="password_change_done"),

    path('password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('register/', register, name="register"),
    path('edit/', profile_edit, name="profile_edit"),
]
