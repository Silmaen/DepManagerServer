"""
Functions to import data from another server
"""

from pathlib import Path

import requests

from scripts.settings import MEDIA_ROOT
from .logger import logger
from .models import PackageEntry


def long_import(url: str, user: str, password: str):
    logger.debug(f"Importing from database {url} with user {user}")

    api_url = "/api2"
    resp = requests.get(
        f"{url}{api_url}", auth=(user, password), timeout=10, verify=False
    )
    if resp.status_code != 200:
        api_url = "/api"
        resp = requests.get(
            f"{url}{api_url}", auth=(user, password), timeout=10, verify=False
        )
        if resp.status_code != 200:
            logger.error(
                f"Failed to connect to {url}: {resp.status_code} - {resp.text}"
            )
            return
        else:
            logger.info(f"Using legacy API at {url}{api_url}")
    http_data = resp.text.splitlines(keepends=False)
    logger.debug(f"Received {len(http_data)} lines of data from {url}")
    added = 0
    for index, line in enumerate(http_data):
        logger.info(f"Processing {index+1}/{len(http_data)}: {line}")
        data = {}
        try:
            predicate, idata = line.strip().split(" ", 1)
            predicate.strip()
            idata.strip()
            name, version = predicate.split("/", 1)
            data["name"] = name.strip()
            data["version"] = version.strip()
            date = ""
            if ")" in idata:
                date, idata = idata.split(")")
                date = date.replace("(", "").strip()
                idata.strip()
            data["date"] = date
            items = idata.replace("[", "").replace("]", "").replace(",", "").split()
            if len(items) not in [4, 5]:
                logger.error(
                    f"WARNING: Bad Line format: '{data}': '{name}' '{version}' '{date}' {items}",
                )
                continue
            data["glibc"] = items[4] if len(items) == 5 else ""
            data["abi"] = items[3][
                0
            ].lower()  # only the first character is the ABI code
            data["os"] = items[2][0].lower()  # only the first character is the OS code
            # arch
            if items[0] == "x86_64":
                data["arch"] = "x"
            if items[0] == "aarch64":
                data["arch"] = "a"
            if items[0] == "any":
                data["arch"] = "y"
            # kind
            if items[1] == "shared":
                data["kind"] = "r"
            if items[1] == "static":
                data["kind"] = "t"
            if items[1] == "header":
                data["kind"] = "h"
            if items[1] == "any":
                data["kind"] = "a"
        except Exception as err:
            logger.error(f"ERROR: bad line format '{line}' ({err})")
            continue
        exists = PackageEntry.objects.filter(
            name=data["name"],
            version=data["version"],
            os=data["os"],
            arch=data["arch"],
            kind=data["kind"],
            abi=data["abi"],
            glibc=data["glibc"],
            build_date=data["date"],
        ).exists()
        if exists:
            logger.debug(f"Package {data['name']} {data['version']} already exists.")
            continue
        else:
            logger.debug(f"Downloading package {data['name']} {data['version']}")
        try:
            # request the package file url
            post_data = {"action": "pull"} | data
            resp = requests.post(
                f"{url}{api_url}",
                data=post_data,
                auth=(user, password),
                timeout=10,
                verify=False,
            )
            if resp.status_code != 200:
                logger.error(
                    f"Failed to get package file URL for {data['name']} {data['version']}: {resp.status_code} - {resp.text}"
                )
                continue
            file_url = resp.text.strip()
            filename = file_url.rsplit("/", 1)[-1]
            resp = requests.get(
                f"{url}{file_url}", auth=(user, password), stream=True, verify=False
            )
            if resp.status_code != 200:
                logger.error(
                    f"Failed to download package file for {data['name']} {data['version']}: {resp.status_code} - {resp.text}"
                )
                continue
            new_path = Path(MEDIA_ROOT) / "packages" / filename
            with open(new_path, "wb") as fp:
                fp.write(resp.content)
            logger.debug(
                f"Package {data['name']} {data['version']} saved to {new_path}"
            )
            entry = PackageEntry(
                name=data["name"],
                version=data["version"],
                os=data["os"],
                arch=data["arch"],
                kind=data["kind"],
                abi=data["abi"],
                glibc=data["glibc"],
                build_date=data["date"],
                package=str(new_path),
            )
            entry.save()
        except Exception as err:
            logger.error(
                f"ERROR: Failed to download package file for {data['name']} {data['version']}: {err}"
            )
            continue
        added += 1
    logger.info(f"Imported {added} packages from {url}")
