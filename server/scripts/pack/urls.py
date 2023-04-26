"""
Fichier définissant les urls
"""
from django.conf.urls.static import static
from django.conf import settings as main_settings
from django.urls import path, include
from .views import *

urlpatterns = [
    path("", index, name="index"),
    path("packages", index, name="package"),
    path("users", index, name="users"),
    path("api", api)
] + static(main_settings.MEDIA_URL, document_root=main_settings.MEDIA_ROOT)