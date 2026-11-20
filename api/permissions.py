from rest_framework.permissions import BasePermission


class IsAnonymous(BasePermission):
    """Replacement for @redirect_if_authenticated: only logged-out users."""
    message = "Anda sudah login."

    def has_permission(self, request, view):
        return not request.user.is_authenticated


class IsStaffOrSuperuser(BasePermission):
    """For admin-only endpoints (mirrors the is_staff / is_superuser check)."""

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))
