"""Puebla la base con datos de demostracion.

Existe para que cualquiera pueda clonar el repo y ver el sistema con contenido
en un comando, sin tener que inventar 20 tickets a mano para una captura.
"""
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.equipos.models import Equipo, TipoEquipo
from apps.tickets.models import Categoria, Comentario, Estado, Prioridad, Ticket
from apps.usuarios.models import Rol

Usuario = get_user_model()

PERSONAS = [
    ("admin", "Matias", "Rojas", Rol.ADMIN, "TI"),
    ("tecnico1", "Camila", "Soto", Rol.TECNICO, "TI"),
    ("tecnico2", "Diego", "Fuentes", Rol.TECNICO, "TI"),
    ("operaciones", "Paula", "Herrera", Rol.USUARIO, "Operaciones"),
    ("bodega", "Luis", "Miranda", Rol.USUARIO, "Bodega"),
    ("contabilidad", "Ana", "Vergara", Rol.USUARIO, "Contabilidad"),
]

EQUIPOS = [
    ("TI-0001", TipoEquipo.NOTEBOOK, "Lenovo", "ThinkPad E14", "Oficina central", "operaciones"),
    ("TI-0002", TipoEquipo.NOTEBOOK, "HP", "ProBook 450", "Oficina central", "contabilidad"),
    ("TI-0003", TipoEquipo.ESCRITORIO, "Dell", "OptiPlex 3080", "Contabilidad", "contabilidad"),
    ("TI-0004", TipoEquipo.IMPRESORA, "Brother", "HL-L2360", "Bodega", "bodega"),
    ("TI-0005", TipoEquipo.RED, "TP-Link", "Archer C80", "Taller", None),
    ("TI-0006", TipoEquipo.SERVIDOR, "HPE", "ProLiant ML30", "Sala de servidores", "tecnico1"),
    ("TI-0007", TipoEquipo.ESCRITORIO, "Lenovo", "ThinkCentre M70", "Operaciones", "operaciones"),
]

INCIDENCIAS = [
    ("El notebook no carga la bateria", Categoria.HARDWARE, Prioridad.ALTA),
    ("No puedo acceder al sistema de facturacion", Categoria.ACCESOS, Prioridad.CRITICA),
    ("La impresora de bodega imprime hojas en blanco", Categoria.HARDWARE, Prioridad.MEDIA),
    ("Internet se cae cada 10 minutos en el taller", Categoria.RED, Prioridad.ALTA),
    ("Excel se cierra solo al abrir el informe mensual", Categoria.SOFTWARE, Prioridad.MEDIA),
    ("Solicito instalacion de cliente VPN", Categoria.SOFTWARE, Prioridad.BAJA),
    ("Pantalla del PC de contabilidad parpadea", Categoria.HARDWARE, Prioridad.MEDIA),
    ("Correo corporativo rechaza adjuntos grandes", Categoria.SOFTWARE, Prioridad.BAJA),
    ("El servidor de archivos responde muy lento", Categoria.RED, Prioridad.CRITICA),
    ("Necesito reset de contrasena del ERP", Categoria.ACCESOS, Prioridad.MEDIA),
    ("Teclado del notebook con teclas pegadas", Categoria.HARDWARE, Prioridad.BAJA),
    ("No aparece la impresora compartida en red", Categoria.RED, Prioridad.MEDIA),
]

DETALLE = (
    "Detectado durante la jornada. Se reinicio el equipo sin resultado. "
    "Adjunto detalle para que soporte pueda revisar."
)


class Command(BaseCommand):
    help = "Crea usuarios, equipos y tickets de ejemplo (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="demo12345", help="Clave para los usuarios de ejemplo.")

    @transaction.atomic
    def handle(self, *args, **opciones):
        random.seed(7)  # mismo set de datos en cada corrida
        clave = opciones["password"]

        usuarios = {}
        for username, nombre, apellido, rol, area in PERSONAS:
            usuario, creado = Usuario.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": nombre,
                    "last_name": apellido,
                    "rol": rol,
                    "area": area,
                    "email": f"{username}@empresa.cl",
                    "is_staff": rol == Rol.ADMIN,
                    "is_superuser": rol == Rol.ADMIN,
                },
            )
            if creado:
                usuario.set_password(clave)
                usuario.save()
            usuarios[username] = usuario

        equipos = []
        for codigo, tipo, marca, modelo, ubicacion, responsable in EQUIPOS:
            equipo, _ = Equipo.objects.get_or_create(
                codigo_interno=codigo,
                defaults={
                    "tipo": tipo,
                    "marca": marca,
                    "modelo": modelo,
                    "ubicacion": ubicacion,
                    "responsable": usuarios.get(responsable),
                    "numero_serie": f"SN{random.randint(100000, 999999)}",
                    "fecha_adquisicion": timezone.now().date() - timedelta(days=random.randint(200, 1500)),
                },
            )
            equipos.append(equipo)

        if Ticket.objects.exists():
            self.stdout.write(self.style.WARNING("Ya existen tickets: no se crean duplicados."))
            self.stdout.write(self.style.SUCCESS(f"Usuarios y equipos verificados. Clave: {clave}"))
            return

        solicitantes = [usuarios[u] for u in ("operaciones", "bodega", "contabilidad")]
        tecnicos = [usuarios["tecnico1"], usuarios["tecnico2"]]
        estados = [Estado.ABIERTO, Estado.EN_PROGRESO, Estado.EN_ESPERA, Estado.RESUELTO, Estado.CERRADO]

        for indice, (titulo, categoria, prioridad) in enumerate(INCIDENCIAS):
            estado = estados[indice % len(estados)]
            ticket = Ticket.objects.create(
                titulo=titulo,
                descripcion=DETALLE,
                categoria=categoria,
                prioridad=prioridad,
                estado=estado,
                solicitante=random.choice(solicitantes),
                tecnico_asignado=None if estado == Estado.ABIERTO else random.choice(tecnicos),
                equipo=random.choice(equipos) if indice % 3 else None,
            )
            # Se envejecen ticket e historico con update() para no pisar
            # auto_now_add; si no, todo quedaria fechado hoy y las capturas
            # mostrarian un "dias abierto" que no calza con el historico.
            creado = timezone.now() - timedelta(days=random.randint(0, 21))
            Ticket.objects.filter(pk=ticket.pk).update(creado_en=creado)
            Comentario.objects.filter(ticket=ticket).update(creado_en=creado)
            if ticket.tecnico_asignado:
                respuesta = Comentario.objects.create(
                    ticket=ticket,
                    autor=ticket.tecnico_asignado,
                    cuerpo="Reviso el caso y te confirmo durante el dia.",
                )
                Comentario.objects.filter(pk=respuesta.pk).update(
                    creado_en=creado + timedelta(hours=random.randint(1, 20))
                )

        self.stdout.write(self.style.SUCCESS(
            f"Demo cargada: {Usuario.objects.count()} usuarios, "
            f"{Equipo.objects.count()} equipos, {Ticket.objects.count()} tickets."
        ))
        self.stdout.write(f"Ingresa como admin / {clave}")
