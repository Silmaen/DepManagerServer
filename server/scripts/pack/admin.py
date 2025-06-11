"""
Definition of admin.
"""

from django.contrib import admin

from .models import *


# Register your models here.
class PackageEntryAdmin(admin.ModelAdmin):
    """
    Admin page for packages
    """

    list_display = (
        "name",
        "version",
        "glibc",
        "os",
        "arch",
        "kind",
        "abi",
        "build_date",
    )
    list_filter = (
        "name",
        "version",
        "glibc",
        "os",
        "arch",
        "kind",
        "abi",
        "build_date",
    )
    date_hierarchy = "date"
    search_fields = (
        "name",
        "version",
        "glibc",
        "os",
        "arch",
        "kind",
        "abi",
        "build_date",
    )
    fieldsets = (
        # Field set 1: name & version
        ("Identity", {"fields": ("name", "version", "build_date")}),
        # Field set 2: types
        ("Identity", {"fields": ("os", "arch", "kind", "abi", "glibc")}),
        # Field set 3: the package file
        ("Files", {"fields": ("package",)}),
    )


admin.site.register(PackageEntry, PackageEntryAdmin)
