from rest_framework.permissions import BasePermission


def _role(request):
    u = request.user
    return getattr(u, "role", None) if u.is_authenticated else None


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return _role(request) == "admin"


class IsStaffRole(BasePermission):
    """Admin or Clinical Staff."""
    def has_permission(self, request, view):
        return _role(request) in ("admin", "clinical")
