"""Mixins de autorizacion por rol.

Centralizarlos evita repetir `if request.user.rol == ...` en cada vista y deja
la regla en un solo lugar cuando haya que cambiarla.
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class RolRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("No tienes permisos para esta seccion.")
        return super().handle_no_permission()


class SoloGestionMixin(RolRequeridoMixin):
    """Tecnicos y administradores."""

    def test_func(self):
        return self.request.user.puede_gestionar_tickets


class SoloAdminMixin(RolRequeridoMixin):
    """Solo administradores: inventario y asignacion de tecnicos."""

    def test_func(self):
        return self.request.user.es_admin
