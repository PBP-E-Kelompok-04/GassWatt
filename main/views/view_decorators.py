from functools import wraps
from django.shortcuts import redirect

def redirect_if_authenticated(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return redirect('main:admin_dashboard')
            else:
                return redirect('main:show_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view