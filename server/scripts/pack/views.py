import shutil
import subprocess
from base64 import b64decode
from pathlib import Path

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import Permission, User
from django.http import HttpResponseForbidden
from django.shortcuts import render, HttpResponse, redirect
from django.views.decorators.csrf import csrf_exempt

from scripts.settings import MEDIA_ROOT
from .forms import PackageEntryForm
from .models import get_package_list, get_package_detail, PackageEntry, get_packages_urls, get_namelist

SiteVersion = "1.0"
SiteHash = "ae0b3f0"


# Create your views here.

def index(request):
    names = get_namelist({})

    return render(request, "index.html",
                  {
                      "title"      : "home",
                      "version"    : {"number": SiteVersion, "hash": SiteHash},
                      "pack_number": len(names),
                  }
                  )


def packages(request):
    if not request.user.is_authenticated:
        return redirect("/")
    if not request.user.has_perm("pack.view_packageentry"):
        return redirect("/")
    ifilter = {}
    if request.method == "POST":
        temp_filter = dict(request.POST)
        for attr in ["name", "version", "os", "arch", "kind", "compiler"]:
            if attr in temp_filter:
                ifilter[attr] = temp_filter[attr][0]
    i_packages = get_package_list(ifilter)
    return render(request, "package.html",
                  {
                      "title"  : "packages",
                      "page"   : "packages",
                      "version": {"number": SiteVersion, "hash": SiteHash},
                      "package": i_packages
                  }
                  )


def detail_package(request, name, version):
    if not request.user.is_authenticated:
        return redirect("/")
    if not request.user.has_perm("pack.view_packageentry"):
        return redirect("/")
    package = get_package_detail(name, version)
    if package is None:
        return redirect("package")
    return render(request, "package_detail.html",
                  {
                      "title"  : f"{name} {version}",
                      "page"   : "packages",
                      "version": {"number": SiteVersion, "hash": SiteHash},
                      "package": package
                  })


def delete_package(request, pk):
    if not request.user.is_authenticated:
        return redirect("/")
    if not request.user.has_perm("pack.view_packageentry"):
        return redirect("/")
    if not request.user.has_perm("pack.delete_packageentry"):
        return redirect("package")
    if request.method == "POST":
        pack = PackageEntry.objects.get(pk=pk)
        pack.delete()
    return redirect("package")


def users(request):
    if not request.user.is_authenticated:
        return redirect("/")
    entries = User.objects.all()
    p_users = []
    for entry in entries:
        p_users.append(
                {
                    "pk"             : entry.pk,
                    "name"           : entry.username,
                    "last_conn"      : entry.last_login,
                    "admin"          : entry.is_superuser,
                    "can_view_pack"  : entry.has_perm("pack.view_packageentry"),
                    "can_add_pack"   : entry.has_perm("pack.add_packageentry"),
                    "can_delete_pack": entry.has_perm("pack.delete_packageentry"),
                    "can_view_user"  : entry.has_perm("auth.view_user"),
                    "can_delete_user": entry.has_perm("auth.delete_user"),
                }
        )
    return render(request, "users.html",
                  {
                      "title"  : "users",
                      "page"   : "users",
                      "version": {"number": SiteVersion, "hash": SiteHash},
                      "users"  : p_users
                  }
                  )


def modif_user(request, pk):
    if not request.user.is_authenticated:
        return redirect("/")
    if not request.user.has_perm("auth.delete_user"):
        return redirect("/")
    if request.method == "POST":
        user = User.objects.get(pk=pk)
        if 'action' not in request.POST:
            return redirect("users")
        if request.POST['action'] == "delete":
            user.delete()
        elif request.POST['action'] == "toggle_user_delete":
            ido = Permission.objects.get(codename="delete_user")
            if user.has_perm("auth.delete_user"):
                user.user_permissions.remove(ido)
            else:
                user.user_permissions.add(ido)
            user.save()
        elif request.POST['action'] == "toggle_user_view":
            ido = Permission.objects.get(codename="view_user")
            if user.has_perm("auth.view_user"):
                user.user_permissions.remove(ido)
            else:
                user.user_permissions.add(ido)
            user.save()
        elif request.POST['action'] == "toggle_pack_view":
            ido = Permission.objects.get(codename="view_packageentry")
            if user.has_perm("pack.view_packageentry"):
                user.user_permissions.remove(ido)
            else:
                user.user_permissions.add(ido)
            user.save()
        elif request.POST['action'] == "toggle_pack_add":
            ido = Permission.objects.get(codename="add_packageentry")
            if user.has_perm("pack.add_packageentry"):
                user.user_permissions.remove(ido)
            else:
                user.user_permissions.add(ido)
            user.save()
        elif request.POST['action'] == "toggle_pack_delete":
            ido = Permission.objects.get(codename="delete_packageentry")
            if user.has_perm("pack.delete_packageentry"):
                user.user_permissions.remove(ido)
            else:
                user.user_permissions.add(ido)
            user.save()
    return redirect("users")


@csrf_exempt
def api(request):
    try:
        if not request.user.is_authenticated:
            if "Authorization" in request.headers:
                try:
                    key, dec = b64decode(request.headers["Authorization"].split()[-1]).decode("ascii").split(":", 1)
                    user = authenticate(request, username=key, password=dec)
                    if user is None:
                        return HttpResponseForbidden(f"""Only authenticated user allowed
    Login: {key}, password: {dec} is invalid.""")
                    login(request, user)
                except Exception as err:
                    return HttpResponseForbidden(f"""Only authenticated user allowed
    Method: {request.method},Headers: {request.headers}
    ERROR: {err}
    """)
            if not request.user.is_authenticated:
                return HttpResponseForbidden(f"""Only authenticated user allowed""")
        if not request.user.has_perm("pack.view_packageentry"):
            return HttpResponseForbidden("Please ask the right to see packages")
        if request.method == "GET":
            resp = ""
            entries = PackageEntry.objects.all()
            for pack in entries:
                resp += f"{pack.to_dep_entry()}\n"
            return HttpResponse(resp)
        if request.method == "POST":
            data = request.POST.dict()
            if "action" not in data:
                return HttpResponse(f"ERROR no asked action.\nPOST: {data}\nheaders: {request.headers}", status=406)
            if data["action"] not in ["push", "pull"]:
                return HttpResponse(f"ERROR invalid action.\nPOST: {data}\nheaders: {request.headers}", status=406)
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
            if data["action"] == "push":
                try:
                    if len(request.FILES.dict()) > 0:
                        form = PackageEntryForm(request.POST, request.FILES)
                        if form.is_valid():
                            form.save()
                            return HttpResponse(
                                    f"GOOD.\nPOST: {data}\nFILES: {request.FILES.dict()}\nheaders: {request.headers}",
                                    status=200)
                        else:
                            form.full_clean()
                            return HttpResponse(
                                    f"INVALID FORM.\nPOST: {data}\nFILES: {request.FILES.dict()}\nheaders: {request.headers}",
                                    status=406)
                    else:
                        if "package.path" in request.POST:
                            # temp file to destination folder
                            origin_path = Path((request.POST["package.path"]))
                            new_path = Path(MEDIA_ROOT) / "packages" / request.POST["package.name"]
                            shutil.move(origin_path, new_path)
                            entry = PackageEntry.objects.create(
                                    name=request.POST["name"],
                                    version=request.POST["version"],
                                    os=request.POST["os"],
                                    arch=request.POST["arch"],
                                    kind=request.POST["kind"],
                                    compiler=request.POST["compiler"],
                                    package=str(new_path)
                            )
                            entry.save()
                            return HttpResponse(
                                    f"GOOD.\nPOST: {data}\nFILES: {request.FILES.dict()}\nheaders: {request.headers}",
                                    status=200)
                        return HttpResponse(
                                f"INVALID FORM.\nPOST: {data}\nFILES: {request.FILES.dict()}\nheaders: {request.headers}",
                                status=406)
                except Exception as excep:
                    oo = subprocess.run("ls /tmp", shell=True, capture_output=True)
                    return HttpResponse(
                            f"ERROR problem with the data: {excep}.\ntemp: {oo.stdout}\nPOST: {data}\nFILES: {request.FILES.dict()}\nheaders: {request.headers}",
                            status=406)

            return HttpResponse(
                    f'ERROR action {data["action"]} not yet implemented.\nPOST: {data}\nheaders: {request.headers}',
                    status=406)
        return HttpResponseForbidden()
    except Exception as err:
        return HttpResponse(f"""Exception during treatment {err}.""", status=406)
