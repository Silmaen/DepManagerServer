"""
Package views
"""

from base64 import b64decode
from pathlib import Path
from shutil import move
from subprocess import run

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import Permission, User
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render, HttpResponse, redirect
from django.views.decorators.csrf import csrf_exempt

from scripts.settings import MEDIA_ROOT, SITE_VERSION, SITE_HASH, SITE_API_VERSION
from .db_locking import locker
from .decorators.database import require_not_locked
from .decorators.permissions import require_auth, require_perm
from .forms import PackageEntryForm
from .logger import logger
from .models import (
    get_package_list,
    get_package_detail,
    PackageEntry,
    get_packages_urls,
    get_entry_count,
    delete_packages,
)
from .task import database_repair, database_import


def index(request):
    """

    :param request:
    :return:
    """
    return render(
        request,
        "index.html",
        {
            "title": "home",
            "version": {"number": SITE_VERSION, "hash": SITE_HASH},
            "pack_number": get_entry_count(),
        },
    )


@require_auth
@require_perm("pack.view_packageentry")
@require_not_locked
def packages(request):
    """

    :param request:
    :return:
    """
    temp_filter = {}
    if request.method == "POST":
        post = dict(request.POST)
        for key in ["os", "arch", "kind", "abi", "name", "version"]:
            if key not in post:
                continue
            temp_filter[key] = post[key][0]
    possible = {
        "os": ["any", "linux", "windows"],
        "arch": ["any", "x86_64", "aarch64"],
        "kind": ["any", "static", "shared", "header"],
        "abi": ["any", "gnu", "llvm", "msvc"],
    }
    i_packages = get_package_list(temp_filter)
    return render(
        request,
        "package.html",
        {
            "title": "packages",
            "page": "packages",
            "version": {"number": SITE_VERSION, "hash": SITE_HASH},
            "package": i_packages,
            "filter": temp_filter,
            "filter_possible": possible,
        },
    )


@require_auth
@require_perm("pack.view_packageentry")
@require_not_locked
def detail_package(request, name):
    """

    :param request:
    :param name:
    :return:
    """
    package = get_package_detail(name)
    if package is None:
        return redirect("package")
    return render(
        request,
        "package_detail.html",
        {
            "title": f"{name}",
            "page": "packages",
            "version": {"number": SITE_VERSION, "hash": SITE_HASH},
            "package": package,
        },
    )


@require_auth
@require_perm("pack.view_packageentry")
@require_perm("pack.delete_packageentry", redirect_url="package")
@require_not_locked
def delete_package(request, pk):
    """

    :param request:
    :param pk:
    :return:
    """
    if request.method == "POST":
        pack = PackageEntry.objects.get(pk=pk)
        pack.delete()
        # Récupérer l'URL de la page précédente
        previous_page = request.META.get("HTTP_REFERER")

        # Rediriger vers la page précédente
        if previous_page:
            return HttpResponseRedirect(previous_page)
    return redirect("package")


@require_auth
@require_perm("pack.view_packageentry")
@require_perm("pack.delete_packageentry", redirect_url="package")
@require_not_locked
def admin_db(request):
    """

    :param request:
    :return:
    """
    return render(
        request,
        "admin.html",
        {
            "title": "Administration",
            "page": "admin",
            "version": {"number": SITE_VERSION, "hash": SITE_HASH},
        },
    )


@require_auth
@require_perm("pack.view_packageentry")
@require_perm("pack.delete_packageentry", redirect_url="package")
@require_not_locked
def db_repair(request):
    """

    :param request:
    :return:
    """
    database_repair()
    return redirect("admin_db")


@require_auth
@require_perm("auth.vew_user")
@require_not_locked
def users(request):
    """

    :param request:
    :return:
    """
    entries = User.objects.all()
    p_users = []
    for entry in entries:
        p_users.append(
            {
                "pk": entry.pk,
                "name": entry.username,
                "last_conn": entry.last_login,
                "admin": entry.is_superuser,
                "can_view_pack": entry.has_perm("pack.view_packageentry"),
                "can_add_pack": entry.has_perm("pack.add_packageentry"),
                "can_delete_pack": entry.has_perm("pack.delete_packageentry"),
                "can_view_user": entry.has_perm("auth.view_user"),
                "can_delete_user": entry.has_perm("auth.delete_user"),
            }
        )
    return render(
        request,
        "users.html",
        {
            "title": "users",
            "page": "users",
            "version": {"number": SITE_VERSION, "hash": SITE_HASH},
            "users": p_users,
        },
    )


@require_auth
@require_perm("auth.delete_user")
@require_not_locked
def modif_user(request, pk):
    """

    :param request:
    :param pk:
    :return:
    """
    if request.method == "POST":
        user = User.objects.get(pk=pk)
        if "action" not in request.POST:
            return redirect("users")
        if request.POST["action"] == "delete":
            user.delete()
        elif request.POST["action"] == "toggle_user_delete":
            ido = Permission.objects.get(codename="delete_user")
            if user.has_perm("auth.delete_user"):
                user.user_permissions.remove(ido)
            else:
                user.user_permissions.add(ido)
            user.save()
        elif request.POST["action"] == "toggle_user_view":
            ido = Permission.objects.get(codename="view_user")
            if user.has_perm("auth.view_user"):
                user.user_permissions.remove(ido)
            else:
                user.user_permissions.add(ido)
            user.save()
        elif request.POST["action"] == "toggle_pack_view":
            ido = Permission.objects.get(codename="view_packageentry")
            if user.has_perm("pack.view_packageentry"):
                user.user_permissions.remove(ido)
            else:
                user.user_permissions.add(ido)
            user.save()
        elif request.POST["action"] == "toggle_pack_add":
            ido = Permission.objects.get(codename="add_packageentry")
            if user.has_perm("pack.add_packageentry"):
                user.user_permissions.remove(ido)
            else:
                user.user_permissions.add(ido)
            user.save()
        elif request.POST["action"] == "toggle_pack_delete":
            ido = Permission.objects.get(codename="delete_packageentry")
            if user.has_perm("pack.delete_packageentry"):
                user.user_permissions.remove(ido)
            else:
                user.user_permissions.add(ido)
            user.save()
    return redirect("users")


@require_auth
@require_perm("pack.view_packageentry")
def maintenance_page(request):
    """

    :param request:
    :return:
    """
    if not locker.is_locked():  # the lock has been released go back to packages
        return redirect("package")
    return render(
        request,
        "maintenance.html",
    )


def auths_required(request):
    """
    Check if the user is authenticated and has the required permissions.
    If not, redirect to the login page or show an error message.
    :param request:
    :return: HttpResponse
    """
    if not request.user.is_authenticated:
        if "Authorization" in request.headers:
            try:
                key, dec = (
                    b64decode(request.headers["Authorization"].split()[-1])
                    .decode("ascii")
                    .split(":", 1)
                )
                user = authenticate(request, username=key, password=dec)
                if user is None:
                    return HttpResponseForbidden(
                        f"""Only authenticated user allowed
    Login: {key}, password: {dec} is invalid."""
                    )
                login(request, user)
            except Exception as err:
                return HttpResponseForbidden(
                    f"""Only authenticated user allowed
    Method: {request.method},Headers: {request.headers}
    ERROR: {err}
    """
                )
        if not request.user.is_authenticated:
            return HttpResponseForbidden(f"""Only authenticated user allowed""")
    return None


@csrf_exempt
def api(request):
    """
    Second version of api, with subversion management and better error handling.
    :param request:
    :return:
    """
    try:
        auth_response = auths_required(request)
        if auth_response is not None:
            return auth_response
        if not request.user.has_perm("pack.view_packageentry"):
            return HttpResponseForbidden("Please ask the right to see packages")

        if locker.is_locked():
            return HttpResponse(
                f"ERROR: Server is under maintenance, try again later.", status=406
            )
        if request.method == "GET":
            entries = PackageEntry.objects.all()
            resp = "\n".join(pack.to_dep_entry() for pack in entries)
            return HttpResponse(resp)
        if request.method == "POST":
            logger.debug(f"POST request on API")
            logger.debug(f"request.body: {request.body}")
            data = request.POST.dict()
            logger.debug(f"request.POST: {data}")

            if "action" not in data:
                return HttpResponse(
                    f"ERROR no asked action.\nPOST: {data}\nheaders: {request.headers}",
                    status=406,
                )
            if data["action"] not in ["pull", "version", "push", "delete"]:
                return HttpResponse(
                    f"ERROR invalid action.\nPOST: {data}\nheaders: {request.headers}",
                    status=406,
                )
            #
            # Convert in case of old format
            if "compiler" in data:
                data["abi"] = data["compiler"]
                data.pop("compiler")
            #
            # no additional credentials required
            if data["action"] == "pull":
                package = get_packages_urls(data)
                if len(package) == 0:
                    return HttpResponse(f"""ERROR No matching package.""", status=406)
                resp = ""
                for pack in package:
                    pack_u = f"{pack}".replace("/data/", "/media/")
                    if not pack_u.startswith("/media/"):
                        pack_u = f"/media/{pack_u}"
                    resp += f"{pack_u}\n"
                return HttpResponse(resp, status=200)
            elif data["action"] == "version":
                return HttpResponse(
                    f"version: {SITE_VERSION}\napi_version: {SITE_API_VERSION}\n",
                    status=200,
                )
            #
            # Need credentials of adding a package
            elif data["action"] == "push":
                if not request.user.has_perm("pack.add_packageentry"):
                    return HttpResponseForbidden(
                        "Please ask the right to push packages"
                    )
                try:
                    if len(request.FILES.dict()) > 0:
                        form = PackageEntryForm(request.POST, request.FILES)
                        if form.is_valid():
                            form.save()
                            return HttpResponse(
                                f"GOOD.\nPOST: {data}\nFILES: {request.FILES.dict()}\nheaders: {request.headers}",
                                status=200,
                            )
                        else:
                            form.full_clean()
                            return HttpResponse(
                                f"INVALID FORM.\nPOST: {data}\nFILES: {request.FILES.dict()}\nheaders: {request.headers}",
                                status=406,
                            )
                    elif "package.path" in data:
                        # temp file to destination folder
                        origin_path = Path((data["package.path"]))
                        new_path = (
                            Path(MEDIA_ROOT) / "packages" / request.POST["package.name"]
                        )
                        move(origin_path, new_path)
                        if "build_date" in data:
                            entry = PackageEntry.objects.create(
                                name=data["name"],
                                version=data["version"],
                                os=data["os"],
                                arch=data["arch"],
                                kind=data["kind"],
                                abi=data["abi"],
                                glibc=data["glibc"],
                                build_date=data["build_date"],
                                package=str(new_path),
                            )
                            entry.save()
                            return HttpResponse(
                                f"GOOD.\nPOST: {data}\nFILES: {request.FILES.dict()}\nheaders: {request.headers}",
                                status=200,
                            )
                        else:
                            entry = PackageEntry.objects.create(
                                name=data["name"],
                                version=data["version"],
                                os=data["os"],
                                arch=data["arch"],
                                kind=data["kind"],
                                abi=data["abi"],
                                package=str(new_path),
                            )
                            entry.save()
                            return HttpResponse(
                                f"WARNING old FORMAT.\nPOST: {data}\nFILES: {request.FILES.dict()}\nheaders: {request.headers}",
                                status=201,
                            )
                    return HttpResponse(
                        f"INVALID REQUEST.\nPOST: {data}\nFILES: {request.FILES.dict()}\nheaders: {request.headers}",
                        status=406,
                    )
                except Exception as err:
                    oo = run("ls /tmp", shell=True, capture_output=True)
                    return HttpResponse(
                        f"ERROR problem with the data: {err}.\ntemp: {oo.stdout}\nPOST: {data}\nFILES: {request.FILES.dict()}\nheaders: {request.headers}",
                        status=406,
                    )
            #
            # Require full credentials on database
            elif data["action"] == "delete":
                if not request.user.has_perm("pack.delete_packageentry"):
                    return HttpResponseForbidden(
                        "Please ask the right to push packages"
                    )
                package = get_packages_urls(data)
                if len(package) == 0:
                    return HttpResponse(f"""ERROR No matching package.""", status=406)
                if len(package) > 1:
                    return HttpResponse(
                        f"""ERROR more than one package match the query.""", status=406
                    )
                delete_packages(data)
                return HttpResponse(f"Entry deleted", status=200)
            return HttpResponse(
                f'ERROR action {data["action"]} not yet implemented.\nPOST: {data}\nheaders: {request.headers}',
                status=406,
            )
        return HttpResponseForbidden()
    except Exception as err:
        return HttpResponse(f"""Exception during treatment {err}.""", status=406)


@require_auth
@require_perm("pack.view_packageentry")
@require_perm("pack.delete_packageentry", redirect_url="package")
@require_not_locked
def repo_clone(request):
    """
    Clone a repository from the server.
    :param request:
    :return:
    """
    if request.method != "POST":
        return redirect("admin_db")
    database_import(
        request.POST.get("url", ""),
        request.POST.get("login", ""),
        request.POST.get("password", ""),
    )
    return redirect("admin_db")
