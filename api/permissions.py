# api/permissions.py
from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    """Permite acceso solo a usuarios ADMIN"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.rol == 'ADMIN'

class IsDoctor(BasePermission):
    """Permite acceso solo a usuarios DOCTOR"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.rol == 'DOCTOR'

class IsPaciente(BasePermission):
    """Permite acceso solo a usuarios PACIENTE"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.rol == 'PACIENTE'

class IsAuthenticated(BasePermission):
    """Cualquier usuario autenticado"""
    def has_permission(self, request, view):
        return request.user.is_authenticated
