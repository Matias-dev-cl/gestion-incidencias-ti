from django import forms

from apps.formularios import EstiloTailwindMixin

from .models import Equipo


class EquipoForm(EstiloTailwindMixin, forms.ModelForm):
    class Meta:
        model = Equipo
        fields = [
            "codigo_interno",
            "tipo",
            "marca",
            "modelo",
            "numero_serie",
            "ubicacion",
            "estado",
            "responsable",
            "fecha_adquisicion",
            "observaciones",
        ]
        widgets = {
            "fecha_adquisicion": forms.DateInput(attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }
