from django.db import models
from django.urls import reverse


class TipoEquipo(models.TextChoices):
    NOTEBOOK = "NOTEBOOK", "Notebook"
    ESCRITORIO = "ESCRITORIO", "PC de escritorio"
    IMPRESORA = "IMPRESORA", "Impresora"
    SERVIDOR = "SERVIDOR", "Servidor"
    RED = "RED", "Equipo de red"
    OTRO = "OTRO", "Otro"


class EstadoEquipo(models.TextChoices):
    OPERATIVO = "OPERATIVO", "Operativo"
    EN_REPARACION = "EN_REPARACION", "En reparacion"
    BAJA = "BAJA", "Dado de baja"


class EquipoQuerySet(models.QuerySet):
    def visibles_para(self, usuario):
        """Quien no es soporte solo ve sus equipos y los compartidos.

        Los equipos sin responsable (impresoras, router del taller) quedan
        visibles para todos a proposito: son los que cualquiera necesita poder
        reportar. El resto del inventario no le incumbe a un usuario comun.
        """
        if usuario.puede_gestionar_tickets:
            return self
        return self.filter(models.Q(responsable=usuario) | models.Q(responsable__isnull=True))


class Equipo(models.Model):
    """Un activo del inventario de TI.

    El codigo interno es la llave con la que la gente lo pide por telefono
    ("el equipo TI-0042 no prende"), por eso es unico y obligatorio, mientras
    que el numero de serie del fabricante puede faltar en equipos antiguos.
    """

    codigo_interno = models.CharField(max_length=30, unique=True)
    tipo = models.CharField(max_length=12, choices=TipoEquipo.choices, db_index=True)
    marca = models.CharField(max_length=60)
    modelo = models.CharField(max_length=80, blank=True)
    numero_serie = models.CharField(max_length=80, blank=True)
    ubicacion = models.CharField(max_length=120, blank=True)
    estado = models.CharField(
        max_length=14,
        choices=EstadoEquipo.choices,
        default=EstadoEquipo.OPERATIVO,
        db_index=True,
    )
    responsable = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipos_a_cargo",
        help_text="Persona que usa habitualmente el equipo.",
    )
    fecha_adquisicion = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    objects = EquipoQuerySet.as_manager()

    class Meta:
        verbose_name = "equipo"
        verbose_name_plural = "equipos"
        ordering = ["codigo_interno"]
        indexes = [models.Index(fields=["tipo", "estado"])]

    def __str__(self):
        return f"{self.codigo_interno} - {self.marca} {self.modelo}".strip()

    def get_absolute_url(self):
        return reverse("equipos:detalle", args=[self.pk])

    @property
    def tickets_abiertos(self):
        from apps.tickets.models import Ticket

        return self.tickets.exclude(estado__in=Ticket.ESTADOS_FINALES).count()
