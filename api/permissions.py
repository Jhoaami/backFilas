from rest_framework.permissions import BasePermission
from .models import User

class IsAdmin(BasePermission):
    """
    Permite el acceso solo a usuarios con el rol de ADMIN.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'rol') and 
            request.user.rol == 'ADMIN'
        )

class IsDoctor(BasePermission):
    """Permite acceso solo a usuarios con rol de Doctor."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.rol == User.Role.DOCTOR