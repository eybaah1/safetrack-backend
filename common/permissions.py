from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Only admin users or Django superusers."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.user_role == "admin" or request.user.is_superuser


class IsAdminOrSecurity(BasePermission):
    """Admin or security personnel."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.user_role in ("admin", "security") or request.user.is_superuser


class IsApproved(BasePermission):
    """Only approved accounts can access the resource."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.account_status == "approved"