from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Estado(models.TextChoices):
    ABIERTO = "ABIERTO", "Abierto"
    EN_PROGRESO = "EN_PROGRESO", "En progreso"
    EN_ESPERA = "EN_ESPERA", "En espera de terceros"
    RESUELTO = "RESUELTO", "Resuelto"
    CERRADO = "CERRADO", "Cerrado"


class Prioridad(models.TextChoices):
    BAJA = "BAJA", "Baja"
    MEDIA = "MEDIA", "Media"
    ALTA = "ALTA", "Alta"
    CRITICA = "CRITICA", "Critica"


class Categoria(models.TextChoices):
    HARDWARE = "HARDWARE", "Hardware"
    SOFTWARE = "SOFTWARE", "Software"
    RED = "RED", "Red y conectividad"
    ACCESOS = "ACCESOS", "Accesos y cuentas"
    OTRO = "OTRO", "Otro"


class TicketQuerySet(models.QuerySet):
    def visibles_para(self, usuario):
        """Un usuario comun solo ve lo suyo; tecnicos y admins ven todo.

        La regla vive en el queryset y no en cada vista para que no exista la
        posibilidad de olvidarla en una vista nueva.
        """
        if usuario.puede_gestionar_tickets:
            return self
        return self.filter(solicitante=usuario)

    def abiertos(self):
        return self.exclude(estado__in=Ticket.ESTADOS_FINALES)

    def con_relaciones(self):
        return self.select_related("solicitante", "tecnico_asignado", "equipo")


class Ticket(models.Model):
    ESTADOS_FINALES = (Estado.RESUELTO, Estado.CERRADO)

    titulo = models.CharField(max_length=140)
    descripcion = models.TextField()
    categoria = models.CharField(
        max_length=10, choices=Categoria.choices, default=Categoria.OTRO, db_index=True
    )
    prioridad = models.CharField(
        max_length=8, choices=Prioridad.choices, default=Prioridad.MEDIA, db_index=True
    )
    estado = models.CharField(
        max_length=12, choices=Estado.choices, default=Estado.ABIERTO, db_index=True
    )
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tickets_solicitados",
    )
    tecnico_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets_asignados",
        limit_choices_to={"rol__in": ["TECNICO", "ADMIN"]},
    )
    equipo = models.ForeignKey(
        "equipos.Equipo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
        help_text="Equipo del inventario afectado, si aplica.",
    )
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    cerrado_en = models.DateTimeField(null=True, blank=True, editable=False)

    objects = TicketQuerySet.as_manager()

    class Meta:
        verbose_name = "ticket"
        verbose_name_plural = "tickets"
        ordering = ["-creado_en"]
        indexes = [models.Index(fields=["estado", "prioridad"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(titulo__gt=""), name="ticket_titulo_no_vacio"
            )
        ]

    def __str__(self):
        return f"#{self.pk} {self.titulo}"

    def get_absolute_url(self):
        return reverse("tickets:detalle", args=[self.pk])

    @property
    def esta_cerrado(self):
        return self.estado in self.ESTADOS_FINALES

    @property
    def dias_abierto(self):
        fin = self.cerrado_en or timezone.now()
        return (fin - self.creado_en).days

    def puede_ver(self, usuario):
        return usuario.puede_gestionar_tickets or self.solicitante_id == usuario.pk


class Comentario(models.Model):
    """Historico del ticket.

    Las notas internas y las entradas automaticas del sistema viven en la misma
    tabla que los comentarios normales: es un solo hilo cronologico, y filtrar
    por dos banderas es mas simple que mantener tres modelos separados.
    """

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comentarios")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="comentarios",
    )
    cuerpo = models.TextField()
    es_interno = models.BooleanField(
        default=False, help_text="Solo visible para tecnicos y administradores."
    )
    es_sistema = models.BooleanField(
        default=False, help_text="Generado automaticamente por un cambio de estado."
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "comentario"
        verbose_name_plural = "comentarios"
        ordering = ["creado_en"]

    def __str__(self):
        return f"Comentario en #{self.ticket_id} por {self.autor or 'sistema'}"
