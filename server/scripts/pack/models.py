"""
Package models.
"""

from datetime import datetime
from pathlib import Path

from django.db import models
from django.utils import timezone

from pack.logger import logger
from scripts.settings import MEDIA_ROOT

old_date = datetime.fromisoformat("2000-01-01T00:00:00+0000")


# Create your models here.
class PackageEntry(models.Model):
    """
    Package in the list.
    """

    OsType = (("l", "Linux"), ("w", "Windows"), ("a", "any"))
    ArchType = (("x", "x86_64"), ("a", "aarch64"), ("y", "any"))
    KindType = (("r", "shared"), ("t", "static"), ("h", "header"), ("a", "any"))
    AbiType = (("g", "gnu-like"), ("l", "llvm"), ("m", "msvc-like"), ("a", "any"))

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
    abi = models.CharField(
        max_length=1, choices=AbiType, verbose_name="Package's abi type.", default="g"
    )
    build_date = models.DateTimeField(
        default=old_date,
        verbose_name="Date of Build",
    )
    date = models.DateTimeField(default=timezone.now, verbose_name="Date of Upload")
    package = models.FileField(upload_to="packages", verbose_name="Package file")

    dependencies = models.TextField(
        default="", verbose_name="Package dependencies", blank=True
    )
    description = models.TextField(
        default="", verbose_name="Package description", blank=True
    )

    class Meta:
        """
        Metadata for the packages
        """

        verbose_name = "C++ Package repository item"

    def check_file(self):
        """
        Check if the file is relative to MEDIA_ROOT, and correct if not.
        """
        file_path = str(self.package)

        # Si le chemin commence par /data/ au lieu de /app/data/
        if file_path.startswith("/data/"):
            # Convertir en chemin relatif
            relative_path = file_path.replace("/data/", "")
            self.package = relative_path
            self.save(update_fields=["package"])
            logger.info(f"Corrected path from {file_path} to {relative_path}")

        # Si le chemin est absolu et commence par MEDIA_ROOT
        elif file_path.startswith(str(MEDIA_ROOT)):
            relative_path = file_path.replace(str(MEDIA_ROOT) + "/", "")
            self.package = relative_path
            self.save(update_fields=["package"])
            logger.info(f"Corrected absolute path to relative: {relative_path}")

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

        for attr in ["name", "version", "os", "arch", "kind", "abi", "glibc"]:
            object_attr = getattr(self, attr)
            if attr in ["os", "arch", "kind", "abi"]:
                if match_to[attr] == "any" or object_attr == "any":
                    # if any, skip the check
                    continue
                if len(match_to[attr]) == 1:
                    if match_to[attr] == "*":
                        # if match_to[attr] is "*", skip the check
                        continue
                    if match_to[attr] != object_attr:
                        return False
                    continue
            if not compile(translate(match_to[attr])).match(object_attr):
                return False
        return True

    def to_dep_entry(self):
        """

        :return:
        """
        if self.glibc == "":
            return f"{self.name}/{self.version} ({self.build_date.isoformat()}) [{self.get_arch_display()}, {self.get_kind_display()}, {self.get_os_display()}, {self.get_abi_display()}]"
        return f"{self.name}/{self.version} ({self.build_date.isoformat()}) [{self.get_arch_display()}, {self.get_kind_display()}, {self.get_os_display()}, {self.get_abi_display()}, {self.glibc}]"

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


def convert_filter(get_filter: dict):
    """
    Convert the filter to a proper format.
    :param get_filter:
    :return:
    """
    true_filter = {
        "name": "*",
        "version": "*",
        "os": "*",
        "arch": "*",
        "kind": "*",
        "abi": "*",
        "glibc": "*",
    }
    if "compiler" in get_filter:
        get_filter["abi"] = get_filter["compiler"]
    for key in ["name", "version", "glibc"]:
        if key in get_filter:
            if get_filter[key] not in [None, ""]:
                true_filter[key] = get_filter[key]
    for key in ["glibc", "os", "arch", "abi"]:
        if key in get_filter and get_filter[key] not in [None, "", "any"]:
            true_filter[key] = get_filter[key][0].lower()
    if "kind" in get_filter and get_filter["kind"] not in [None, "", "any"]:
        if get_filter["kind"] == "shared":
            true_filter["kind"] = "r"
        elif get_filter["kind"] == "static":
            true_filter["kind"] = "t"
        elif get_filter["kind"] == "header":
            true_filter["kind"] = "h"
    return true_filter


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
        "abi",
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
    loc_abi = data["abi"]
    for key, val in PackageEntry.AbiType:
        if loc_abi == key:
            key_ok = True
            break
        if loc_abi.lower() == val.split("-")[0]:
            loc_abi = key
            key_ok = True
            break
    if not key_ok:
        logger.warning(
            f"Cannot create entry: bad ABI key {loc_abi} vs. {PackageEntry.AbiType}."
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
            abi=loc_abi,
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
    true_filter = convert_filter(get_filter)
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


def get_package_detail(name: str, get_filter: dict = {}):
    """

    :param name:
    :return:
    """
    it = {
        "name": name,
        "versions": {},
        "description": "",
        "dependencies": [],
    }
    true_filter = convert_filter(get_filter)
    query = PackageEntry.objects.filter(name=name)
    latest_entry = None
    latest_date = old_date
    for q in query:
        if not q.match(true_filter):
            continue
        q.check_file()
        if q.build_date is None:
            q.build_date = old_date
            q.save()
        # Track latest entry for description
        if q.build_date > latest_date:
            latest_date = q.build_date
            latest_entry = q
        combination = {
            "os": q.get_os_display(),
            "arch": q.get_arch_display(),
            "kind": q.get_kind_display(),
            "abi": q.get_abi_display(),
            "glibc": q.glibc,
            "build_date": q.build_date,
            "package": q.package,
            "package_size": q.get_pretty_size_display(),
            "pk": q.pk,
        }
        if q.version not in it["versions"].keys():
            it["versions"][q.version] = []
        it["versions"][q.version].append(combination)
    # Get description from latest entry
    if latest_entry and latest_entry.description:
        it["description"] = latest_entry.description
    if latest_entry and latest_entry.dependencies:
        try:
            import datetime

            it["dependencies"] = eval(latest_entry.dependencies)
        except Exception as e:
            logger.warning(
                f"Cannot parse dependencies of ({latest_entry.name}/{latest_entry.version}) '{latest_entry.dependencies}' : {e}"
            )
            it["dependencies"] = []
    return sort_a(it)


def get_package_list(get_filter):
    """

    :param get_filter:
    :return:
    """
    names = get_namelist(get_filter)
    result = []
    for name in names:
        result.append(get_package_detail(name, get_filter))
    return result


def get_packages_urls(get_filter: dict):
    """

    :param get_filter:
    :return:
    """
    true_filter = convert_filter(get_filter)
    for key in true_filter.keys():
        if key in get_filter:
            if get_filter[key] not in [None, "", "any"]:
                true_filter[key] = get_filter[key]
    query = PackageEntry.objects.all()
    url_list = []
    for q in query:
        if not q.match(true_filter):
            continue
        q.check_file()
        url_list.append(q.package)
    return url_list


def delete_packages(delete_filter: dict):
    """

    :param delete_filter:
    :return:
    """
    true_filter = convert_filter(delete_filter)
    for key in true_filter.keys():
        if key in delete_filter:
            if delete_filter[key] not in [None, "", "any"]:
                true_filter[key] = delete_filter[key]
    query = PackageEntry.objects.all()
    count = 0
    for q in query:
        if not q.match(true_filter):
            continue
        q.check_file()
        count += 1
        q.delete()
    return count
