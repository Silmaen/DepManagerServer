"""
Database Repairing actions.
"""

from datetime import datetime
from pathlib import Path

from .logger import logger
from .models import PackageEntry, old_date, safe_create


def get_file_infos(file: Path):
    """
    Try to open archive file to get package metadata.
    :param file: The file name.
    :return: The data read in archive.
    """
    import tarfile

    if file.suffix != ".tgz":
        logger.warning(f"Non-archive file in package dir: {file.name}")
        return {}
    with tarfile.open(file, "r:gz") as archive:
        logger.info(f"getting info for archive: {archive.name}")
        try:
            data = {
                "name": "",
                "version": "",
                "os": "",
                "arch": "",
                "kind": "",
                "abi": "",
                "glibc": "",
                "build_date": old_date,
                "dependencies": [],
            }
            # test if info.yaml is present
            if "./info.yaml" in archive.getnames():
                logger.info(f"Archive has new format info.yaml.")
                infos = archive.extractfile("./info.yaml")
                import yaml

                with open(infos, "r") as infos_file:
                    content = yaml.safe_load(infos)
                    for key in data.keys():
                        if key in content.keys():
                            if key == "build_date":
                                if "+" not in content[key]:
                                    content[key] += "+0000"
                                data[key] = datetime.fromisoformat(content[key])
                                continue
                            data[key] = content[key]
            else:
                logger.warn("Archive has old format info.")
                infos = archive.extractfile("./edp.info")
                content = infos.read().decode("utf-8")
                # for line in infos.readlines():
                #    line = line.decode("utf-8")
                for line in content.splitlines(keepends=False):
                    if "#" in line:
                        line = line.split("#")[0].strip()
                    if "=" not in line:
                        continue
                    key, val = [it.strip() for it in line.split("=", 1)]
                    if key == "compiler":
                        key = "abi"  # we use abi instead of compiler
                    if key in data.keys():
                        if key == "build_date":
                            if "+" not in val:
                                val += "+0000"
                            data[key] = datetime.fromisoformat(val)
                            continue
                        data[key] = val
            return data
        except KeyError:
            logger.warning(
                f"Archive file {file.name} does not seems to have informations file"
            )
    return {}


def long_repair(do_correct: bool = False, skip_large_files: bool = True):
    """
    Repair the database by looking into files.
    """
    start = datetime.now()
    total_error_count = 0
    total_error_corrected = 0
    try:
        #
        # FIRST PASS: check if local file correspond to database entry
        #
        logger.info("Starting database repair...")
        logger.info("Checking local files against database entries...")
        query = PackageEntry.objects.all()
        if len(query) == 0:
            logger.info("Nothing in the query.")
            return
        pack_dir = Path(query[0].package.path).parent
        counter = -1
        for file in pack_dir.iterdir():
            counter += 1
            if skip_large_files and file.stat().st_size > 6 * 1024 * 1024:
                logger.warning(f"{counter:08d} file: {file.name} skipping large file.")
                continue
            file_error_count = 0
            file_error_corrected = 0
            in_db = PackageEntry.objects.filter(package__endswith=f"/{file.name}")
            data = get_file_infos(file)
            if len(in_db) == 0:
                logger.warning(
                    f"{counter:08d} file: {file.name} not referenced in the database, need to be added {data}."
                )
                total_error_count += 1
                if do_correct:
                    entry = safe_create(data, file)
                    if entry is not None:
                        entry.save()
                        total_error_corrected += 1
                continue
            elif len(in_db) > 1:
                logger.warning(
                    f"{counter:08d} file: {file.name} referenced multiple times in the database, keep only the best entry."
                )
                total_error_count += 1
                if do_correct:
                    for i in range(len(in_db)):
                        if i == 0:
                            continue  # we keep thi one
                        in_db[i].delete(keep_file=True)
                    total_error_corrected += 1
            pack = in_db[0]
            db_data = {
                "name": pack.name,
                "version": pack.version,
                "os": pack.get_os_display(),
                "arch": pack.get_arch_display(),
                "kind": pack.get_kind_display(),
                "abi": pack.get_abi_display().split("-")[0],
                "glibc": pack.glibc,
                "build_date": pack.build_date,
            }
            if len(data) == 0:
                total_error_count += 1
                continue
            for key in data.keys():
                if data[key] != db_data[key]:
                    logger.warning(
                        f"{counter:08d} file: {file.name} different {key}: {data[key]} vs. {db_data[key]}."
                    )
                    if do_correct:
                        try:
                            setattr(pack, key, data[key])
                            pack.save()
                            file_error_corrected += 1
                        except Exception as err:
                            logger.error(f"While trying to correct file: {err}")
                    file_error_count += 1
            if file_error_count > 0:
                total_error_count += 1
                if file_error_count == file_error_corrected:
                    total_error_corrected += 1
            else:
                pass
        #
        # SECOND PASS: check database entries
        #
        logger.info("Checking database entries...")
        # redo the query after first corrections
        query = PackageEntry.objects.all()
        for item in query:
            if item.package.path in ["", None]:
                logger.warning(f"Database entry {item.pk}: field 'file' is empty.")
                total_error_count += 1
                continue
            if not Path(item.package.path).resolve().exists():
                logger.warning(
                    f"Database entry {item.pk}: field 'file' does not refer to existing file."
                )
                total_error_count += 1
                continue

    except Exception as err:
        logger.error(f"Exception during database repair: {err}.")
    duration = datetime.now() - start
    logger.info(
        f"Database repaired issue: {total_error_corrected} / {total_error_count} -- database size: {PackageEntry.objects.count()} in {duration}."
    )
