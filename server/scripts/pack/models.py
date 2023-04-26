from django.db import models
from django.utils import timezone


# Create your models here.
class PackageEntry(models.Model):
    """
    Package in the list
    """
    OsType = (('l', 'Linux'), ("w", "Windows"))
    ArchType = (("x", "x86_64"), ("a", "aarch64"))
    KindType = (("r", "shared"), ("t", "static"), ("h", "header"), ("a", "any"))
    CompilerType = (("g", "gnu-like"), ("m", "msvc-like"))

    name = models.CharField(
            max_length=60,
            verbose_name="Package's Name."
    )
    version = models.CharField(
            max_length=25,
            verbose_name="Package's Version."
    )
    os = models.CharField(
            max_length=1,
            choices=OsType,
            verbose_name="Package's Operating System."
    )
    arch = models.CharField(
            max_length=1,
            choices=ArchType,
            verbose_name="Package's CPU Architecture."
    )
    kind = models.CharField(
            max_length=1,
            choices=KindType,
            verbose_name="Package's kind."
    )
    compiler = models.CharField(
            max_length=1,
            choices=CompilerType,
            verbose_name="Package's compiler type."
    )
    date = models.DateTimeField(
            default=timezone.now,
            verbose_name="Date of Creation")
    package = models.FileField(
            upload_to='packages',
            verbose_name="Package file")

    class Meta:
        """
        Meta data for the packages
        """
        verbose_name = "C++ Package repository item"

    def save(self, *args, **kwargs):
        """
        Overload of the save procedure to check the date
        TODO: format the package name with the hash.
        """
        self.date = timezone.now()
        super(PackageEntry, self).save(*args, **kwargs)

    def to_dict(self):
        """
        Get a dictionary of data.
        :return: Dictionary.
        """
        return {
            "name"    : self.name,
            "version" : self.version,
            "os"      : self.os,
            "arch"    : self.arch,
            "kind"    : self.kind,
            "compiler": self.compiler
        }

    def hash(self):
        """
        Get a hash for dependency infos.
        :return: The hash as string.
        """
        from hashlib import sha1
        hash_ = sha1()
        glob = f"{self.name}{self.version}{self.os}{self.arch}{self.kind}{self.compiler}"
        hash_.update(glob.encode())
        return str(hash_.hexdigest())

    def get_as_str(self):
        """
        Get a human-readable string.
        :return: A string.
        """
        return F"  {self.name}/{self.version} [{self.arch}, {self.kind}, {self.os}, {self.compiler}]"
