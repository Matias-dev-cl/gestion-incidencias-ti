from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "get_full_name", "email", "rol", "area", "is_active")
    list_filter = ("rol", "is_active", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email", "area")
    fieldsets = UserAdmin.fieldsets + (
        ("Datos de soporte", {"fields": ("rol", "area", "telefono")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Datos de soporte", {"fields": ("rol", "area", "telefono")}),
    )
