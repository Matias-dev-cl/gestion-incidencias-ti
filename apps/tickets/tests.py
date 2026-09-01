"""Tests de las reglas que no son obvias leyendo los modelos.

No se testea que Django guarde en la base: se testean las decisiones propias
del dominio (quien ve que, y que pasa al cambiar de estado).
"""
from django.test import TestCase
from django.urls import reverse

from apps.equipos.models import Equipo, EstadoEquipo, TipoEquipo
from apps.usuarios.models import Rol, Usuario

from .models import Estado, Ticket


class BaseDatos(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_user("admin", password="x", rol=Rol.ADMIN)
        cls.tecnico = Usuario.objects.create_user("tec", password="x", rol=Rol.TECNICO)
        cls.ana = Usuario.objects.create_user("ana", password="x", rol=Rol.USUARIO)
        cls.beto = Usuario.objects.create_user("beto", password="x", rol=Rol.USUARIO)
        cls.equipo = Equipo.objects.create(
            codigo_interno="TI-9001", tipo=TipoEquipo.NOTEBOOK, marca="Lenovo"
        )
        cls.ticket = Ticket.objects.create(
            titulo="No enciende", descripcion="Nada", solicitante=cls.ana, equipo=cls.equipo
        )


class VisibilidadPorRol(BaseDatos):
    def test_usuario_solo_ve_sus_tickets(self):
        visibles = Ticket.objects.visibles_para(self.beto)
        self.assertNotIn(self.ticket, visibles)
        self.assertIn(self.ticket, Ticket.objects.visibles_para(self.ana))

    def test_tecnico_y_admin_ven_todo(self):
        for usuario in (self.tecnico, self.admin):
            self.assertIn(self.ticket, Ticket.objects.visibles_para(usuario))

    def test_detalle_ajeno_devuelve_404(self):
        self.client.force_login(self.beto)
        respuesta = self.client.get(reverse("tickets:detalle", args=[self.ticket.pk]))
        self.assertEqual(respuesta.status_code, 404)

    def test_usuario_comun_no_puede_crear_equipos(self):
        self.client.force_login(self.ana)
        respuesta = self.client.get(reverse("equipos:crear"))
        self.assertEqual(respuesta.status_code, 403)


class EfectosDelCambioDeEstado(BaseDatos):
    def test_al_crear_se_registra_una_entrada_de_sistema(self):
        self.assertTrue(self.ticket.comentarios.filter(es_sistema=True).exists())

    def test_resolver_sella_la_fecha_de_cierre(self):
        self.ticket.estado = Estado.RESUELTO
        self.ticket.save()
        self.ticket.refresh_from_db()
        self.assertIsNotNone(self.ticket.cerrado_en)

    def test_reabrir_limpia_la_fecha_de_cierre(self):
        self.ticket.estado = Estado.CERRADO
        self.ticket.save()
        self.ticket.estado = Estado.ABIERTO
        self.ticket.save()
        self.ticket.refresh_from_db()
        self.assertIsNone(self.ticket.cerrado_en)

    def test_el_equipo_queda_en_reparacion_y_vuelve_a_operativo(self):
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado, EstadoEquipo.EN_REPARACION)

        self.ticket.estado = Estado.CERRADO
        self.ticket.save()
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado, EstadoEquipo.OPERATIVO)


class Autoasignacion(BaseDatos):
    def test_tecnico_toma_el_ticket_y_pasa_a_en_progreso(self):
        self.client.force_login(self.tecnico)
        self.client.post(reverse("tickets:autoasignar", args=[self.ticket.pk]))
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.tecnico_asignado, self.tecnico)
        self.assertEqual(self.ticket.estado, Estado.EN_PROGRESO)

    def test_usuario_comun_no_puede_autoasignarse(self):
        self.client.force_login(self.ana)
        respuesta = self.client.post(reverse("tickets:autoasignar", args=[self.ticket.pk]))
        self.assertEqual(respuesta.status_code, 403)


class RenderizadoConRelacionesVacias(BaseDatos):
    """Un ticket sin tecnico y un equipo sin responsable deben renderizar igual.

    Regresion: encadenar el filtro `default` sobre una relacion nula rompia la
    plantilla, porque el argumento del filtro se resuelve aunque el valor
    anterior sea valido.
    """

    def test_bandeja_con_ticket_sin_tecnico(self):
        self.client.force_login(self.tecnico)
        respuesta = self.client.get(reverse("tickets:lista"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Sin asignar")

    def test_inventario_con_equipo_sin_responsable(self):
        self.client.force_login(self.tecnico)
        respuesta = self.client.get(reverse("equipos:lista"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Sin asignar")

    def test_detalle_muestra_traza_del_sistema(self):
        self.client.force_login(self.ana)
        respuesta = self.client.get(reverse("tickets:detalle", args=[self.ticket.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ticket creado")


class BorradoDeTicket(BaseDatos):
    def test_borrar_el_ultimo_ticket_devuelve_el_equipo_a_operativo(self):
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado, EstadoEquipo.EN_REPARACION)

        self.ticket.delete()
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado, EstadoEquipo.OPERATIVO)


class AlcanceDelInventario(BaseDatos):
    """El inventario completo es informacion de soporte, no de todo el mundo."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.equipo_de_beto = Equipo.objects.create(
            codigo_interno="TI-9002",
            tipo=TipoEquipo.ESCRITORIO,
            marca="Dell",
            responsable=cls.beto,
        )
        # Sin responsable: es un equipo compartido y lo ve cualquiera.
        cls.compartido = Equipo.objects.create(
            codigo_interno="TI-9003", tipo=TipoEquipo.IMPRESORA, marca="Brother"
        )
        cls.equipo_de_ana = Equipo.objects.create(
            codigo_interno="TI-9004",
            tipo=TipoEquipo.NOTEBOOK,
            marca="HP",
            responsable=cls.ana,
        )

    def test_usuario_ve_los_suyos_y_los_compartidos(self):
        visibles = Equipo.objects.visibles_para(self.beto)
        self.assertIn(self.equipo_de_beto, visibles)
        self.assertIn(self.compartido, visibles)
        self.assertNotIn(self.equipo_de_ana, visibles)

    def test_soporte_ve_todo_el_inventario(self):
        for usuario in (self.tecnico, self.admin):
            self.assertIn(self.equipo_de_beto, Equipo.objects.visibles_para(usuario))

    def test_detalle_de_equipo_ajeno_devuelve_404(self):
        self.client.force_login(self.ana)
        respuesta = self.client.get(reverse("equipos:detalle", args=[self.equipo_de_beto.pk]))
        self.assertEqual(respuesta.status_code, 404)

    def test_el_formulario_no_ofrece_equipos_ajenos(self):
        from .forms import TicketForm

        opciones = TicketForm(usuario=self.beto).fields["equipo"].queryset
        self.assertIn(self.equipo_de_beto, opciones)
        self.assertIn(self.compartido, opciones)
        self.assertNotIn(self.equipo_de_ana, opciones)


class Reapertura(BaseDatos):
    def test_el_solicitante_puede_reabrir_su_ticket_resuelto(self):
        self.ticket.tecnico_asignado = self.tecnico
        self.ticket.estado = Estado.RESUELTO
        self.ticket.save()

        self.client.force_login(self.ana)
        self.client.post(
            reverse("tickets:reabrir", args=[self.ticket.pk]),
            {"motivo": "Volvio a fallar al dia siguiente."},
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado, Estado.EN_PROGRESO)
        self.assertIsNone(self.ticket.cerrado_en)
        self.assertTrue(self.ticket.comentarios.filter(cuerpo__startswith="Volvio").exists())

    def test_sin_tecnico_vuelve_a_la_cola_como_abierto(self):
        self.ticket.estado = Estado.CERRADO
        self.ticket.save()
        self.client.force_login(self.ana)
        self.client.post(reverse("tickets:reabrir", args=[self.ticket.pk]))
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado, Estado.ABIERTO)

    def test_un_tercero_no_puede_reabrir_un_ticket_ajeno(self):
        self.ticket.estado = Estado.RESUELTO
        self.ticket.save()
        self.client.force_login(self.beto)
        self.client.post(reverse("tickets:reabrir", args=[self.ticket.pk]))
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado, Estado.RESUELTO)


class PaginasDeError(BaseDatos):
    """Las plantillas de error deben renderizar sin depender de la vista.

    Se prueban con el renderizador directo porque el cliente de tests corre con
    DEBUG heredado y no siempre pasa por los manejadores personalizados.
    """

    def test_las_plantillas_de_error_renderizan(self):
        from django.template.loader import render_to_string

        for plantilla in ("404.html", "403.html", "500.html"):
            with self.subTest(plantilla=plantilla):
                html = render_to_string(plantilla, {"user": self.ana})
                self.assertIn("<", html)

    def test_un_equipo_ajeno_devuelve_la_pagina_404(self):
        otro = Equipo.objects.create(
            codigo_interno="TI-9100", tipo=TipoEquipo.NOTEBOOK, marca="Acer", responsable=self.beto
        )
        self.client.force_login(self.ana)
        respuesta = self.client.get(reverse("equipos:detalle", args=[otro.pk]))
        self.assertEqual(respuesta.status_code, 404)
