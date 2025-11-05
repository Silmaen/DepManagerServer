"""
Decorators for user permissions.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.models import Permission
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _


def user_capability_required(capability):
    """
    Decorator that checks if the user has a specific capability.
    Capabilities are ordered can_<action>_<what>
    with <action> in [add, edit, delete, view]
    and with priority: delete > edit > add > view
    """

    def decorator(view_func):
        """
        Checks if the user has sufficient capability to access the view.
        :param view_func: The view function to be decorated.
        :return: The wrapped view function.
        """

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            """
            Wrapper function that performs the capability check.
            :param request: The HTTP request object.
            :param args: Positional arguments for the view function.
            :param kwargs: Keyword arguments for the view function.
            :return: The result of the view function if access is granted, otherwise redirects to home with an error message.
            """
            if not request.user.is_authenticated:
                messages.error(
                    request,
                    _("You must be logged in to access this page."),
                )
                return redirect("index")

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            if has_capability(request.user, capability):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(
                    request,
                    _(
                        "Access denied. You do not have the required permissions to access this page."
                    ),
                )
                return redirect("index")

        return wrapper

    return decorator


import logging

django_logger = logging.getLogger("pack")


def toggle_capability(request, user, capability):
    """
    Toggle a specific capability for a user.
    :param request: The HTTP request object.
    :param user: The user object.
    :param capability: The capability to toggle.
    """
    perm_map_set = {
        "can_view_package": ["pack.view_packageentry"],
        "can_add_package": ["pack.view_packageentry", "pack.add_packageentry"],
        "can_delete_package": [
            "pack.view_packageentry",
            "pack.add_packageentry",
            "pack.delete_packageentry",
        ],
        "can_view_user": ["auth.view_user"],
        "can_delete_user": ["auth.delete_user", "auth.view_user"],
    }
    perm_map_unset = {
        "can_view_package": [
            "pack.view_packageentry",
            "pack.add_packageentry",
            "pack.delete_packageentry",
        ],
        "can_add_package": [
            "pack.add_packageentry",
            "pack.delete_packageentry",
        ],
        "can_delete_package": [
            "pack.delete_packageentry",
        ],
        "can_view_user": ["auth.delete_user", "auth.view_user"],
        "can_delete_user": ["auth.delete_user"],
    }
    if capability not in perm_map_set.keys():
        messages.error(request, _("Capability not recognized."))
        return
    if has_capability(user, capability):
        # Remove permissions
        for perm in perm_map_unset[capability]:
            ido = Permission.objects.get(codename=perm.split(".")[1])
            user.user_permissions.remove(ido)
        user.save()

        messages.success(
            request,
            _(
                f"Capability '{capability}' has been removed from user {user.username} by {request.user.username}."
            ),
        )
    else:
        # Add permissions
        for perm in perm_map_set[capability]:
            ido = Permission.objects.get(codename=perm.split(".")[1])
            user.user_permissions.add(ido)
        user.save()

        messages.success(
            request,
            _(
                f"Capability '{capability}' has been granted to user {user.username} by {request.user.username}."
            ),
        )


def has_capability(user, capability):
    """
    Retrieve the capabilities of a user.
    :param user: The user object.
    :param capability: The capability to check.
    :return: A dictionary with capabilities as keys and boolean values indicating if the user has that capability.
    """
    perm_map = {
        # to view a package, one must only have the view permission
        "can_view_package": [
            "pack.view_packageentry",
        ],
        # to add a package, one must be able to view it
        "can_add_package": [
            "pack.view_packageentry",
            "pack.add_packageentry",
        ],
        # to delete a package, one must be able to view and add it
        "can_delete_package": [
            "pack.view_packageentry",
            "pack.add_packageentry",
            "pack.delete_packageentry",
        ],
        # to view a user, one must only have the view permission
        "can_view_user": ["auth.view_user"],
        # to delete a user, one must be able to view it
        "can_delete_user": ["auth.view_user", "auth.delete_user"],
    }
    if capability == "is_admin":
        return user.is_superuser
    if capability in perm_map:
        perms = perm_map[capability]
        for perm in perms:
            if not user.has_perm(perm):
                return False
        return True
    return False


def get_capability(user):
    """
    Retrieve the capabilities of a user.
    :param user: The user object.
    :return: A dictionary with capabilities as keys and boolean values indicating if the user has that capability.
    """
    perms = [
        "can_view_package",
        "can_add_package",
        "can_delete_package",
        "can_view_user",
        "can_delete_user",
        "is_admin",
    ]
    capabilities = {}
    for capability in perms:
        capabilities[capability] = has_capability(user, capability)
    return capabilities
