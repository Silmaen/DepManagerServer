from functools import wraps
from django.shortcuts import redirect


def require_not_locked(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        from pack.db_locking import locker

        if locker.is_locked():
            return redirect("maintenance")
        return view_func(request, *args, **kwargs)

    return _wrapped
