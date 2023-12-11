"""
Package models.
"""
from datetime import datetime
from pathlib import Path

from django.db import models
from django.utils import timezone

from pack.logger import logger

old_date = datetime.fromisoformat("2000-01-01T00:00:00+0000")


# Create your models here.
class PackageEntry(models.Model):
    """
    Package in the list.
    """

    OsType = (("l", "Linux"), ("w", "Windows"), ("a", "any"))
    ArchType = (("x", "x86_64"), ("a", "aarch64"), ("y", "any"))
    KindType = (("r", "shared"), ("t", "static"), ("h", "header"), ("a", "any"))
    CompilerType = (("g", "gnu-like"), ("m", "msvc-like"), ("a", "any"))

    name = models.CharField(max_length=60, verbose_name="Package's Name.")
    version = models.CharField(max_length=25, verbose_name="Package's Version.")
    os = models.CharField(
        max_length=1, choices=OsType, verbose_name="Package's Operating System."
    )
    glibc = models.CharField(
        max_length=25, default="", verbose_name="Package's glibc Version if applicable."
    )
    arch = models.CharField(
        max_length=1, choices=ArchType, verbose_name="Package's CPU Architecture."
    )
    kind = models.CharField(
        max_length=1, choices=KindType, verbose_name="Package's kind."
    )
    compiler = models.CharField(
        max_length=1, choices=CompilerType, verbose_name="Package's compiler type."
    )
    build_date = models.DateTimeField(
        default=old_date,
        verbose_name="Date of Build",
    )
    date = models.DateTimeField(default=timezone.now, verbose_name="Date of Upload")
    package = models.FileField(upload_to="packages", verbose_name="Package file")

    class Meta:
        """
        Metadata for the packages
        """

        verbose_name = "C++ Package repository item"

    def save(self, *args, **kwargs):
        """
        Overload of the save procedure to check the date
        :param args:
        :param kwargs:
        """
        self.date = timezone.now()
        super(PackageEntry, self).save(*args, **kwargs)

    def delete(self, keep_file: bool = False, *args, **kwargs):
        """

        :param keep_file:
        :param args:
        :param kwargs:
        """
        if Path(self.package.path).exists() and not keep_file:
            self.package.delete()
        super(PackageEntry, self).delete(*args, **kwargs)

    def match(self, match_to):
        """

        :param match_to:
        :return:
        """
        from fnmatch import translate
        from re import compile

        for attr in ["name", "version", "os", "arch", "kind", "compiler", "glibc"]:
            if attr == "kind" and (
                match_to[attr] == "any" or getattr(self, attr) == "any"
            ):
                continue
            if not compile(translate(match_to[attr])).match(getattr(self, attr)):
                return False
        return True

    def to_dep_entry(self):
        """

        :return:
        """
        if self.glibc == "":
            return f"{self.name}/{self.version} ({self.build_date.isoformat()}) [{self.get_arch_display()}, {self.get_kind_display()}, {self.get_os_display()}, {self.get_compiler_display()}]"
        return f"{self.name}/{self.version} ({self.build_date.isoformat()}) [{self.get_arch_display()}, {self.get_kind_display()}, {self.get_os_display()}, {self.get_compiler_display()}, {self.glibc}]"

    def get_pretty_size_display(self):
        """

        :return:
        """
        if not Path(self.package.path).exists():
            return f"(void)"
        raw_size = Path(self.package.path).stat().st_size
        for unite in ["", "K", "M", "G", "T"]:
            if raw_size < 1024.0:
                break
            raw_size /= 1024.0
        return f"{raw_size:.2f} {unite}"


def safe_create(data: dict, file: Path):
    """

    :param data:
    :param file:
    :return:
    """
    is_ok = True
    for key in [
        "name",
        "version",
        "os",
        "arch",
        "kind",
        "compiler",
        "glibc",
        "build_date",
    ]:
        if key not in data.keys():
            is_ok = False
            logger.warning(f"Cannot create entry: missing key {key}")
    if not file.exists():
        logger.warning(f"Cannot create entry: file does not exists.")
        is_ok = False
    key_ok = False
    loc_os = data["os"]
    for key, val in PackageEntry.OsType:
        if loc_os == key:
            key_ok = True
            break
        if loc_os == val:
            loc_os = key
            key_ok = True
            break
    if not key_ok:
        logger.warning(f"Cannot create entry: bad OS key.")
        is_ok = False
    #
    key_ok = False
    loc_arch = data["arch"]
    for key, val in PackageEntry.ArchType:
        if loc_arch == key:
            key_ok = True
            break
        if loc_arch.lower() == val:
            loc_arch = key
            key_ok = True
            break
    if not key_ok:
        logger.warning(
            f"Cannot create entry: bad ARCH key: {loc_arch} vs. {PackageEntry.ArchType}."
        )
        is_ok = False
    #
    key_ok = False
    loc_kind = data["kind"]
    for key, val in PackageEntry.KindType:
        if loc_kind == key:
            key_ok = True
            break
        if loc_kind.lower() == val:
            loc_kind = key
            key_ok = True
            break
    if not key_ok:
        logger.warning(
            f"Cannot create entry: bad KIND key {loc_kind} vs. {PackageEntry.KindType}."
        )
        is_ok = False
    #
    key_ok = False
    loc_compiler = data["compiler"]
    for key, val in PackageEntry.CompilerType:
        if loc_compiler == key:
            key_ok = True
            break
        if loc_compiler.lower() == val.split("-")[0]:
            loc_compiler = key
            key_ok = True
            break
    if not key_ok:
        logger.warning(
            f"Cannot create entry: bad COMPILER key {loc_compiler} vs. {PackageEntry.CompilerType}."
        )
        is_ok = False
    #
    if is_ok:
        return PackageEntry.objects.create(
            name=data["name"],
            version=data["version"],
            os=loc_os,
            arch=loc_arch,
            kind=loc_kind,
            compiler=loc_compiler,
            glibc=data["glibc"],
            build_date=data["build_date"],
            package=str(file),
        )
    return None


def get_entry_count():
    """

    :return:
    """
    query = PackageEntry.objects.all()
    name_list = []
    for q in query:
        name_list.append(q.name)
    name_list = list(set(name_list))
    return len(name_list)


def get_namelist(get_filter: dict):
    """

    :param get_filter:
    :return:
    """
    true_filter = {
        "name": "*",
        "version": "*",
        "os": "*",
        "arch": "*",
        "kind": "*",
        "compiler": "*",
        "glibc": "*",
    }

    for key in true_filter.keys():
        if key in get_filter:
            if get_filter[key] not in [None, "", "any"]:
                true_filter[key] = get_filter[key]
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
    """

    :param infos:
    :return:
    """
    from copy import deepcopy

    def safe_int(val):
        """

        :param val:
        :return:
        """
        try:
            return int(val)
        except:
            return val

    skey = sorted(
        infos["versions"].keys(),
        key=lambda vers: [safe_int(i) for i in vers.split(".")],
        reverse=True,
    )
    s_infos = deepcopy(infos)
    s_infos["versions"] = {}
    for key in skey:
        s_infos["versions"][key] = sorted(
            infos["versions"][key],
            key=lambda flavor: flavor["build_date"],
            reverse=True,
        )
    return s_infos


def get_package_detail(name: str):
    """

    :param name:
    :return:
    """
    it = {
        "name": name,
        "versions": {},
    }
    query = PackageEntry.objects.filter(name=name)
    for q in query:
        if q.build_date is None:
            q.build_date = old_date
            q.save()
        combination = {
            "os": q.get_os_display(),
            "arch": q.get_arch_display(),
            "kind": q.get_kind_display(),
            "compiler": q.get_compiler_display(),
            "glibc": q.glibc,
            "build_date": q.build_date,
            "package": q.package,
            "package_size": q.get_pretty_size_display(),
            "pk": q.pk,
        }
        if q.version not in it["versions"].keys():
            it["versions"][q.version] = []
        it["versions"][q.version].append(combination)
    return sort_a(it)


def get_package_list(get_filter):
    """

    :param get_filter:
    :return:
    """
    names = get_namelist(get_filter)
    result = []
    for name in names:
        result.append(get_package_detail(name))
    return result


def get_packages_urls(get_filter: dict):
    """

    :param get_filter:
    :return:
    """
    true_filter = {
        "name": "*",
        "version": "*",
        "os": "*",
        "arch": "*",
        "kind": "*",
        "compiler": "*",
        "glibc": "*",
    }
    for key in true_filter.keys():
        if key in get_filter:
            if get_filter[key] not in [None, "", "any"]:
                true_filter[key] = get_filter[key]
    query = PackageEntry.objects.all()
    url_list = []
    for q in query:
        if not q.match(true_filter):
            continue
        url_list.append(q.package)
    return url_list


def delete_packages(delete_filter: dict):
    """

    :param delete_filter:
    :return:
    """
    true_filter = {
        "name": "*",
        "version": "*",
        "os": "*",
        "arch": "*",
        "kind": "*",
        "compiler": "*",
        "glibc": "*",
    }
    for key in true_filter.keys():
        if key in delete_filter:
            if delete_filter[key] not in [None, "", "any"]:
                true_filter[key] = delete_filter[key]
    query = PackageEntry.objects.all()
    count = 0
    for q in query:
        if not q.match(true_filter):
            continue
        count += 1
        q.delete()
    return count
