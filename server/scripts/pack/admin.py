from django.contrib import admin
from .models import *


# Register your models here.
class PackageEntryAdmin(admin.ModelAdmin):
    """
    Admin page for packages
    """
    list_display = (
        'name', 'version', 'os', 'arch', 'kind', 'compiler'
    )
    list_filter = (
        'name', 'version', 'os', 'arch', 'kind', 'compiler'
    )
    date_hierarchy = 'date'
    search_fields = ('name', 'version', 'os', 'arch', 'kind', 'compiler')
    fieldsets = (
        # Fieldset 1: name & version
        ('Indentity', {'fields': ('name', 'version')}),
        # Fieldset 2: types
        ('Indentity', {'fields': ('os', 'arch', 'kind', 'compiler')}),
        # Fieldset 3: the package file
        ('Files', {'fields': ('package',)}),
    )

admin.site.register(PackageEntry, PackageEntryAdmin)
