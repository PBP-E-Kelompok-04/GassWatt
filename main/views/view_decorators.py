from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect


def _is_admin(user):
    return user.is_staff or user.is_superuser

def redirect_if_authenticated(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if _is_admin(request.user):
                return redirect('main:admin_dashboard')
            else:
                return redirect('main:show_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    # Login required, harus staff/superuser
    # Anonymous users ke LOGIN_URL, users biasa dapat 403 page

    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not _is_admin(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper

def admin_required_json(view_func):
    # Seperti admin_required, tapi user biasa dapat json 403 (untuk AJAX endpoints)

    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not _is_admin(request.user):
            return JsonResponse(
                {"status": "error", "message": "Akses ditolak."}, status=403
            )
        return view_func(request, *args, **kwargs)

    return wrapper