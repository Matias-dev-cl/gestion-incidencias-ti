"""Estilos compartidos de formularios.

Vive fuera de las apps para que `equipos` no tenga que importar de `tickets`
solo para reutilizar unas clases de CSS.
"""
from django import forms

CLASES_INPUT = (
    "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm "
    "text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 "
    "focus:ring-sky-200"
)
CLASES_CHECKBOX = "h-4 w-4 rounded border-slate-300 text-sky-600"


class EstiloTailwindMixin:
    """Aplica las clases de Tailwind a los widgets generados por Django."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            if isinstance(campo.widget, forms.CheckboxInput):
                campo.widget.attrs.setdefault("class", CLASES_CHECKBOX)
            else:
                campo.widget.attrs.setdefault("class", CLASES_INPUT)
