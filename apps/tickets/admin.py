from django.contrib import admin

from .models import Comentario, Estado, Ticket


class ComentarioInline(admin.TabularInline):
    model = Comentario
    extra = 0
    fields = ("autor", "cuerpo", "es_interno", "es_sistema", "creado_en")
    readonly_fields = ("creado_en",)
    autocomplete_fields = ("autor",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "titulo", "estado", "prioridad", "categoria", "solicitante", "tecnico_asignado", "creado_en")
    list_filter = ("estado", "prioridad", "categoria", "tecnico_asignado")
    search_fields = ("titulo", "descripcion", "solicitante__username", "equipo__codigo_interno")
    autocomplete_fields = ("solicitante", "tecnico_asignado", "equipo")
    list_select_related = ("solicitante", "tecnico_asignado", "equipo")
    date_hierarchy = "creado_en"
    inlines = [ComentarioInline]
    actions = ["marcar_resueltos"]

    @admin.action(description="Marcar los tickets seleccionados como resueltos")
    def marcar_resueltos(self, request, queryset):
        # Se guarda uno por uno a proposito: un update() masivo se saltaria las
        # senales que sellan la fecha de cierre y escriben el historico.
        actualizados = 0
        for ticket in queryset.exclude(estado=Estado.RESUELTO):
            ticket.estado = Estado.RESUELTO
            ticket.save()
            actualizados += 1
        self.message_user(request, f"{actualizados} ticket(s) marcados como resueltos.")


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ("ticket", "autor", "es_interno", "es_sistema", "creado_en")
    list_filter = ("es_interno", "es_sistema")
    search_fields = ("cuerpo",)
