from django.db import models
from django.utils import timezone


# Create your models here.
class PackageEntry(models.Model):
    """
    Package in the list
    """
    OsType = (('l', 'Linux'), ("w", "Windows"), ("a", "any"))
    ArchType = (("x", "x86_64"), ("a", "aarch64"), ("y", "any"))
    KindType = (("r", "shared"), ("t", "static"), ("h", "header"), ("a", "any"))
    CompilerType = (("g", "gnu-like"), ("m", "msvc-like"), ("a", "any"))

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
        """
        self.date = timezone.now()
        super(PackageEntry, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.package.delete()
        super(PackageEntry, self).delete(*args, **kwargs)

    def match(self, match_to):
        from fnmatch import translate
        from re import compile
        for attr in ["name", "version", "os", "arch", "kind", "compiler"]:
            if attr == "kind" and (match_to[attr] == "any" or getattr(self, attr) == "any"):
                continue
            if not compile(translate(match_to[attr])).match(getattr(self, attr)):
                return False
        return True

    def to_dep_entry(self):
        return f"  {self.name}/{self.version} [{self.get_arch_display()}, {self.get_kind_display()}, {self.get_os_display()}, {self.get_compiler_display()}]"


def get_namelist(filter: dict):
    true_filter = {
        "name"    : "*",
        "version" : "*",
        "os"      : "*",
        "arch"    : "*",
        "kind"    : "*",
        "compiler": "*"
    }

    for key in true_filter.keys():
        if key in filter:
            if filter[key] not in [None, "", "any"]:
                true_filter[key] = filter[key]
    debugstr = f"   filter   : {filter} <br>\n"
    debugstr += f" true filter: {true_filter} <br>\n"
    query = PackageEntry.objects.all()
    name_list = []
    for q in query:
        if not q.match(true_filter):
            continue
        name_list.append((q.name, q.version))
    name_list = list(set(name_list))
    return name_list


def get_package_detail(name: str, version: str):
    it = {"name"        : name,
          "version"     : version,
          "combinations": []}
    query = PackageEntry.objects.filter(name=name, version=version)
    for q in query:
        it["combinations"].append({
            "os"      : q.get_os_display(),
            "arch"    : q.get_arch_display(),
            "kind"    : q.get_kind_display(),
            "compiler": q.get_compiler_display(),
            "package" : q.package,
            "pk"      : q.pk
        })
    return it


def get_package_list(filter):
    names = get_namelist(filter)
    result = []
    for name in names:
        result.append(get_package_detail(name[0], name[1]))
    return result


def get_packages_urls(filter: dict):
    true_filter = {
        "name"    : "*",
        "version" : "*",
        "os"      : "*",
        "arch"    : "*",
        "kind"    : "*",
        "compiler": "*"
    }
    for key in true_filter.keys():
        if key in filter:
            if filter[key] not in [None, "", "any"]:
                true_filter[key] = filter[key]
    query = PackageEntry.objects.all()
    url_list = []
    for q in query:
        if not q.match(true_filter):
            continue
        url_list.append(q.package)
    return url_list
