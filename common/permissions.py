from rest_framework.permissions import BasePermission

class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.user.is_superuser or
            getattr(getattr(request.user, "profile", None), "role", None) == "admin"
        ))

class IsManagerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = getattr(getattr(request.user, "profile", None), "role", None)
        return request.user.is_superuser or role in {"admin", "manager"}
