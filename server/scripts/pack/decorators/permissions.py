from functools import wraps
from django.shortcuts import redirect


def require_auth(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("/")
        return view_func(request, *args, **kwargs)

    return _wrapped


def require_perm(perm, redirect_url="/"):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.has_perm(perm):
                return redirect(redirect_url)
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
