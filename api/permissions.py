from rest_framework.permissions import BasePermission
from .models import User

class IsAdmin(BasePermission):
    """Permite acceso solo a usuarios con rol de Admin."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.rol == User.Role.ADMIN

class IsDoctor(BasePermission):
    """Permite acceso solo a usuarios con rol de Doctor."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.rol == User.Role.DOCTOR