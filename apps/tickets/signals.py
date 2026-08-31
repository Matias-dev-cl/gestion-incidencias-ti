"""Efectos secundarios de un cambio de estado de ticket.

Se resuelven con senales y no dentro de la vista porque tambien deben ocurrir
cuando el cambio viene del admin de Django o de un comando de management.
"""
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from apps.equipos.models import EstadoEquipo
from .models import Comentario, Estado, Ticket


@receiver(pre_save, sender=Ticket)
def registrar_cambio_de_estado(sender, instance, **kwargs):
    """Guarda el estado anterior y sella la fecha de cierre."""
    instance._estado_anterior = None
    if instance.pk:
        instance._estado_anterior = (
            Ticket.objects.filter(pk=instance.pk).values_list("estado", flat=True).first()
        )

    if instance.estado in Ticket.ESTADOS_FINALES and instance.cerrado_en is None:
        instance.cerrado_en = timezone.now()
    elif instance.estado not in Ticket.ESTADOS_FINALES:
        instance.cerrado_en = None


@receiver(post_save, sender=Ticket)
def dejar_traza_en_el_historico(sender, instance, created, **kwargs):
    anterior = getattr(instance, "_estado_anterior", None)

    if created:
        Comentario.objects.create(
            ticket=instance,
            autor=instance.solicitante,
            cuerpo=f"Ticket creado con prioridad {instance.get_prioridad_display()}.",
            es_sistema=True,
        )
    elif anterior and anterior != instance.estado:
        etiquetas = dict(Estado.choices)
        Comentario.objects.create(
            ticket=instance,
            autor=instance.tecnico_asignado,
            cuerpo=f"Estado: {etiquetas.get(anterior, anterior)} -> {instance.get_estado_display()}.",
            es_sistema=True,
        )

    sincronizar_estado_del_equipo(instance.equipo)


@receiver(post_delete, sender=Ticket)
def resincronizar_al_borrar(sender, instance, **kwargs):
    """Borrar el ultimo ticket abierto debe devolver el equipo a operativo."""
    sincronizar_estado_del_equipo(instance.equipo)


def sincronizar_estado_del_equipo(equipo):
    """Un equipo con incidencias abiertas no puede figurar como operativo.

    Un equipo dado de BAJA se excluye a proposito: la baja es una decision
    administrativa y ningun ticket deberia revertirla.
    """
    if equipo is None or equipo.estado == EstadoEquipo.BAJA:
        return

    tiene_abiertos = equipo.tickets.abiertos().exists()
    nuevo = EstadoEquipo.EN_REPARACION if tiene_abiertos else EstadoEquipo.OPERATIVO
    if equipo.estado != nuevo:
        equipo.estado = nuevo
        equipo.save(update_fields=["estado", "actualizado_en"])
