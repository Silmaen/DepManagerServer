"""Packages forms"""

from django.forms import ModelForm

from .models import PackageEntry


class PackageEntryForm(ModelForm):
    class Meta:
        """
        Metadata of package form.
        """

        model = PackageEntry
        fields = [
            "name",
            "version",
            "glibc",
            "build_date",
            "os",
            "arch",
            "kind",
            "abi",
            "package",
        ]
