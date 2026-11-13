from rest_framework.permissions import BasePermission

from apps.identity.models import Role


class _HasRole(BasePermission):
    role: str

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == self.role)


class IsFarmer(_HasRole):
    role = Role.FARMER


class IsBuyer(_HasRole):
    role = Role.BUYER


class IsAdmin(_HasRole):
    role = Role.ADMIN
