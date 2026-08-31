from django.contrib.auth.models import AbstractUser
from django.db import models


class Rol(models.TextChoices):
    """Los tres roles del sistema.

    Se modelan como un campo en el usuario y no como Groups de Django porque
    aqui el rol es exclusivo (un usuario es una cosa u otra) y se consulta en
    casi todas las vistas: un CharField indexado es mas simple de leer y no
    obliga a un JOIN extra en cada request.
    """

    ADMIN = "ADMIN", "Administrador"
    TECNICO = "TECNICO", "Tecnico"
    USUARIO = "USUARIO", "Usuario"


class Usuario(AbstractUser):
    rol = models.CharField(
        max_length=10, choices=Rol.choices, default=Rol.USUARIO, db_index=True
    )
    area = models.CharField(
        max_length=80, blank=True, help_text="Area o departamento al que pertenece."
    )
    telefono = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["first_name", "last_name", "username"]

    def __str__(self):
        nombre = self.get_full_name().strip()
        return f"{nombre or self.username} ({self.get_rol_display()})"

    @property
    def es_admin(self):
        return self.rol == Rol.ADMIN or self.is_superuser

    @property
    def es_tecnico(self):
        return self.rol == Rol.TECNICO

    @property
    def puede_gestionar_tickets(self):
        """Tecnicos y admins pueden cambiar estado, asignar y ver todo."""
        return self.es_admin or self.es_tecnico
