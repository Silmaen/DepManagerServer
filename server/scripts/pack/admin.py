from django.contrib import admin

from .models import *


# Register your models here.
class PackageEntryAdmin(admin.ModelAdmin):
    """
    Admin page for packages
    """
    list_display = (
        'name', 'version', 'glibc', 'os', 'arch', 'kind', 'compiler', 'build_date'
    )
    list_filter = (
        'name', 'version', 'glibc', 'os', 'arch', 'kind', 'compiler', 'build_date'
    )
    date_hierarchy = 'date'
    search_fields = ('name', 'version', 'glibc', 'os', 'arch', 'kind', 'compiler', 'build_date')
    fieldsets = (
        # Fieldset 1: name & version
        ('Indentity', {'fields': ('name', 'version', 'build_date')}),
        # Fieldset 2: types
        ('Indentity', {'fields': ('os', 'arch', 'kind', 'compiler', 'glibc')}),
        # Fieldset 3: the package file
        ('Files', {'fields': ('package',)}),
    )


admin.site.register(PackageEntry, PackageEntryAdmin)
