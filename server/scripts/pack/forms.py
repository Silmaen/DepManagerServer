"""Packages forms"""
from django.forms import ModelForm

from .models import PackageEntry


class PackageEntryForm(ModelForm):
    class Meta:
        model = PackageEntry
        fields = ["name", "version", "os", "arch", "kind", "compiler", "package"]
