from django.contrib import admin

from .models import Equipo


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ("codigo_interno", "tipo", "marca", "modelo", "estado", "ubicacion", "responsable")
    list_filter = ("tipo", "estado")
    search_fields = ("codigo_interno", "marca", "modelo", "numero_serie", "ubicacion")
    autocomplete_fields = ("responsable",)
    list_select_related = ("responsable",)
    date_hierarchy = "creado_en"
    fieldsets = (
        ("Identificacion", {"fields": ("codigo_interno", "tipo", "marca", "modelo", "numero_serie")}),
        ("Situacion", {"fields": ("estado", "ubicacion", "responsable", "fecha_adquisicion")}),
        ("Notas", {"fields": ("observaciones",), "classes": ("collapse",)}),
    )
