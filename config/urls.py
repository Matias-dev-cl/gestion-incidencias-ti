from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Gestion de Incidencias TI"
admin.site.site_title = "Incidencias TI"
admin.site.index_title = "Administracion del sistema"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cuentas/", include("apps.usuarios.urls")),
    path("equipos/", include("apps.equipos.urls")),
    path("", include("apps.tickets.urls")),
]
