from django import forms

from apps.formularios import CLASES_CHECKBOX, EstiloTailwindMixin

from .models import Comentario, Estado, Ticket


class TicketForm(EstiloTailwindMixin, forms.ModelForm):
    """Lo que llena quien reporta la incidencia.

    No incluye estado ni tecnico asignado: eso no lo decide el solicitante.
    """

    class Meta:
        model = Ticket
        fields = ["titulo", "descripcion", "categoria", "prioridad", "equipo"]
        widgets = {
            "descripcion": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Que pasa, desde cuando y que intentaste."}
            ),
            "titulo": forms.TextInput(attrs={"placeholder": "Resumen en una linea"}),
        }
        labels = {"equipo": "Equipo afectado (opcional)"}


class GestionTicketForm(EstiloTailwindMixin, forms.ModelForm):
    """Lo que puede tocar el area de soporte."""

    class Meta:
        model = Ticket
        fields = ["estado", "prioridad", "tecnico_asignado", "equipo"]

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo un admin reasigna a otra persona; el tecnico se toma el ticket.
        if usuario is not None and not usuario.es_admin:
            self.fields.pop("tecnico_asignado")


class ComentarioForm(EstiloTailwindMixin, forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ["cuerpo", "es_interno"]
        widgets = {
            "cuerpo": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Escribe una respuesta o una nota de avance."}
            )
        }
        labels = {"es_interno": "Nota interna (no visible para el solicitante)"}

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario is not None and not usuario.puede_gestionar_tickets:
            self.fields.pop("es_interno")


class FiltroTicketsForm(forms.Form):
    """Filtros de la bandeja. Todos opcionales y combinables."""

    q = forms.CharField(required=False, label="Buscar")
    estado = forms.ChoiceField(required=False, choices=[("", "Todos los estados")] + Estado.choices)
    prioridad = forms.ChoiceField(required=False, choices=[("", "Toda prioridad")] + Ticket._meta.get_field("prioridad").choices)
    categoria = forms.ChoiceField(required=False, choices=[("", "Toda categoria")] + Ticket._meta.get_field("categoria").choices)
    mios = forms.BooleanField(required=False, label="Solo asignados a mi")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base = (
            "rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm "
            "text-slate-700 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
        )
        for nombre, campo in self.fields.items():
            if nombre == "mios":
                campo.widget.attrs["class"] = CLASES_CHECKBOX
            else:
                campo.widget.attrs["class"] = base
        self.fields["q"].widget.attrs["placeholder"] = "Titulo, descripcion o codigo de equipo"
