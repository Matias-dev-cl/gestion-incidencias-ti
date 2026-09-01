from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, TemplateView, View

from apps.equipos.models import Equipo, EstadoEquipo
from apps.usuarios.mixins import SoloGestionMixin

from .forms import ComentarioForm, FiltroTicketsForm, GestionTicketForm, TicketForm
from .models import Estado, Prioridad, Ticket


class DashboardView(LoginRequiredMixin, TemplateView):
    """Resumen de una pantalla.

    Las cifras se calculan con agregaciones en la base y no en Python para que
    el dashboard no dependa del tamano de la tabla de tickets.
    """

    template_name = "tickets/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        usuario = self.request.user
        tickets = Ticket.objects.visibles_para(usuario)

        por_estado = {
            fila["estado"]: fila["total"]
            for fila in tickets.values("estado").annotate(total=Count("id"))
        }
        por_prioridad = {
            fila["prioridad"]: fila["total"]
            for fila in tickets.abiertos().values("prioridad").annotate(total=Count("id"))
        }

        ctx["metricas"] = [
            ("Abiertos", tickets.abiertos().count(), "sky"),
            ("En progreso", por_estado.get(Estado.EN_PROGRESO, 0), "amber"),
            ("Resueltos", por_estado.get(Estado.RESUELTO, 0), "emerald"),
            ("Criticos abiertos", por_prioridad.get(Prioridad.CRITICA, 0), "rose"),
        ]
        ctx["por_estado"] = [
            (etiqueta, por_estado.get(valor, 0)) for valor, etiqueta in Estado.choices
        ]
        ctx["total"] = tickets.count()
        ctx["recientes"] = tickets.con_relaciones()[:8]
        ctx["sin_asignar"] = (
            tickets.abiertos().filter(tecnico_asignado__isnull=True).count()
            if usuario.puede_gestionar_tickets
            else 0
        )
        ctx["equipos_en_reparacion"] = Equipo.objects.filter(
            estado=EstadoEquipo.EN_REPARACION
        ).count()
        return ctx


class TicketListView(LoginRequiredMixin, ListView):
    template_name = "tickets/lista.html"
    context_object_name = "tickets"
    paginate_by = 15

    def get_queryset(self):
        qs = Ticket.objects.visibles_para(self.request.user).con_relaciones()
        self.filtro = FiltroTicketsForm(self.request.GET or None)

        if self.filtro.is_valid():
            datos = self.filtro.cleaned_data
            if datos.get("q"):
                termino = datos["q"]
                qs = qs.filter(
                    Q(titulo__icontains=termino)
                    | Q(descripcion__icontains=termino)
                    | Q(equipo__codigo_interno__icontains=termino)
                )
            for campo in ("estado", "prioridad", "categoria"):
                if datos.get(campo):
                    qs = qs.filter(**{campo: datos[campo]})
            if datos.get("mios") and self.request.user.puede_gestionar_tickets:
                qs = qs.filter(tecnico_asignado=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filtro"] = self.filtro
        return ctx


class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = TicketForm
    template_name = "tickets/formulario.html"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "usuario": self.request.user}

    def form_valid(self, form):
        form.instance.solicitante = self.request.user
        respuesta = super().form_valid(form)
        messages.success(self.request, "Ticket #%s creado." % self.object.pk)
        return respuesta


class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Ticket
    template_name = "tickets/detalle.html"
    context_object_name = "ticket"

    def get_queryset(self):
        return Ticket.objects.visibles_para(self.request.user).con_relaciones()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        usuario = self.request.user
        comentarios = self.object.comentarios.select_related("autor")
        if not usuario.puede_gestionar_tickets:
            comentarios = comentarios.filter(es_interno=False)
        ctx["comentarios"] = comentarios
        ctx["form_comentario"] = ComentarioForm(usuario=usuario)
        if usuario.puede_gestionar_tickets:
            ctx["form_gestion"] = GestionTicketForm(instance=self.object, usuario=usuario)
        return ctx


class ComentarioCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        if not ticket.puede_ver(request.user):
            messages.error(request, "No puedes comentar este ticket.")
            return redirect("tickets:lista")

        form = ComentarioForm(request.POST, usuario=request.user)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.ticket = ticket
            comentario.autor = request.user
            comentario.save()
            messages.success(request, "Comentario agregado.")
        else:
            messages.error(request, "El comentario no puede estar vacio.")
        return redirect(ticket.get_absolute_url())


class GestionTicketView(SoloGestionMixin, View):
    """Cambio de estado, prioridad, equipo y asignacion."""

    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        form = GestionTicketForm(request.POST, instance=ticket, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Ticket actualizado.")
        else:
            messages.error(request, "No se pudo actualizar el ticket.")
        return redirect(ticket.get_absolute_url())


class AutoasignarView(SoloGestionMixin, View):
    """Un tecnico toma un ticket sin esperar a que un admin se lo asigne."""

    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        ticket.tecnico_asignado = request.user
        if ticket.estado == Estado.ABIERTO:
            ticket.estado = Estado.EN_PROGRESO
        ticket.save()
        messages.success(request, "Tomaste el ticket #%s." % ticket.pk)
        return redirect(reverse("tickets:detalle", args=[ticket.pk]))
