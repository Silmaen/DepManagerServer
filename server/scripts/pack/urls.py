"""
Fichier définissant les urls
"""
from django.conf import settings as main_settings
from django.conf.urls.static import static
from django.urls import path

from .views import *

urlpatterns = [
                  path("", index, name="index"),
                  path("packages", packages, name="package"),
                  path("package/<str:name>", detail_package, name="detail_package"),
                  path("package_delete/<int:pk>", delete_package, name="delete_package"),
                  path("users", users, name="users"),
                  path("user/<int:pk>", modif_user, name="modif_user"),
                  path("api", api)
              ] + static(main_settings.MEDIA_URL, document_root=main_settings.MEDIA_ROOT)
