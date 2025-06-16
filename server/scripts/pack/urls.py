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
    path("maintenance", maintenance_page, name="maintenance"),
    path("users", users, name="users"),
    path("user/<int:pk>", modif_user, name="modif_user"),
    path("api", api),
    path("admin_db", admin_db, name="admin_db"),
    path("db_repair", db_repair, name="db_repair"),
    path("repo_clone", repo_clone, name="clone_repository"),
] + static(main_settings.MEDIA_URL, document_root=main_settings.MEDIA_ROOT)
