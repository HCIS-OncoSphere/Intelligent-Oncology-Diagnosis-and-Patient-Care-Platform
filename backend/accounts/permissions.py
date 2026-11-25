from rest_framework.permissions import BasePermission


def _role(request):
    u = request.user
    return getattr(u, "role", None) if u.is_authenticated else None


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return _role(request) == "admin"

    def has_object_permission(self, request, view, obj):
        # Delegate object-level check to view-level check for consistency
        return self.has_permission(request, view)


class IsBillingStaff(BasePermission):
    """The people who raise invoices, take payments and change the price list: finance staff (and admins as a
    back-up). To make billing finance-only, drop "admin" here."""
    def has_permission(self, request, view):
        return _role(request) in ("finance", "admin")

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsBillingReader(BasePermission):
    """Who may read the price list, ICD-10 codes and every invoice: billing staff plus doctors."""
    def has_permission(self, request, view):
        return _role(request) in ("finance", "admin", "clinical")

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsStaffRole(BasePermission):
    """Admin or Clinical Staff."""
    def has_permission(self, request, view):
        return _role(request) in ("admin", "clinical")

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
