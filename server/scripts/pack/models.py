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
    glibc = models.CharField(
            max_length=25,
            default="",
            verbose_name="Package's glibc Version if applicable."
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
    build_date = models.DateTimeField(
            default=timezone.now,
            verbose_name="Date of Build")
    date = models.DateTimeField(
            default=timezone.now,
            verbose_name="Date of Upload")
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
        for attr in ["name", "version", "os", "arch", "kind", "compiler", "glibc"]:
            if attr == "kind" and (match_to[attr] == "any" or getattr(self, attr) == "any"):
                continue
            if not compile(translate(match_to[attr])).match(getattr(self, attr)):
                return False
        return True

    def to_dep_entry(self):
        if self.glibc == "":
            return f"{self.name}/{self.version} ({self.build_date.isoformat()}) [{self.get_arch_display()}, {self.get_kind_display()}, {self.get_os_display()}, {self.get_compiler_display()}]"
        return f"{self.name}/{self.version} ({self.build_date.isoformat()}) [{self.get_arch_display()}, {self.get_kind_display()}, {self.get_os_display()}, {self.get_compiler_display()}, {self.glibc}]"


def get_entry_count():
    query = PackageEntry.objects.all()
    name_list = []
    for q in query:
        name_list.append(q.name)
    name_list = list(set(name_list))
    return len(name_list)


def get_namelist(filter: dict):
    true_filter = {
        "name"    : "*",
        "version" : "*",
        "os"      : "*",
        "arch"    : "*",
        "kind"    : "*",
        "compiler": "*",
        "glibc"   : "*"
    }

    for key in true_filter.keys():
        if key in filter:
            if filter[key] not in [None, "", "any"]:
                true_filter[key] = filter[key]
    query = PackageEntry.objects.all()
    name_list = []
    for q in query:
        if not q.match(true_filter):
            continue
        name_list.append(q.name)
    name_list = list(set(name_list))
    name_list.sort()
    return name_list


def sort_a(infos):
    from copy import deepcopy
    def safe_int(val):
        try:
            return int(val)
        except:
            return val

    skey = sorted(infos["versions"].keys(), key=lambda vers: [safe_int(i) for i in vers.split(".")], reverse=True)
    s_infos = deepcopy(infos)
    s_infos["versions"] = {}
    for key in skey:
        s_infos["versions"][key] = sorted(infos["versions"][key], key=lambda flavor: flavor["build_date"], reverse=True)
    return s_infos


def get_package_detail(name: str):
    it = {"name"    : name,
          "versions": {},
          }
    query = PackageEntry.objects.filter(name=name)
    for q in query:
        combination = {
            "os"        : q.get_os_display(),
            "arch"      : q.get_arch_display(),
            "kind"      : q.get_kind_display(),
            "compiler"  : q.get_compiler_display(),
            "glibc"     : q.glibc,
            "build_date": q.build_date,
            "package"   : q.package,
            "pk"        : q.pk
        }
        if q.version not in it["versions"].keys():
            it["versions"][q.version] = []
        it["versions"][q.version].append(combination)
    return sort_a(it)


def get_package_list(filter):
    names = get_namelist(filter)
    result = []
    for name in names:
        result.append(get_package_detail(name))
    return result


def get_packages_urls(filter: dict):
    true_filter = {
        "name"    : "*",
        "version" : "*",
        "os"      : "*",
        "arch"    : "*",
        "kind"    : "*",
        "compiler": "*",
        "glibc"   : "*"
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
