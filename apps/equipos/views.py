from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.tickets.models import Ticket
from apps.usuarios.mixins import SoloAdminMixin

from .forms import EquipoForm
from .models import Equipo


class EquipoListView(LoginRequiredMixin, ListView):
    model = Equipo
    template_name = "equipos/lista.html"
    context_object_name = "equipos"
    paginate_by = 20

    def get_queryset(self):
        qs = Equipo.objects.select_related("responsable").annotate(
            abiertos=Count("tickets", filter=~Q(tickets__estado__in=Ticket.ESTADOS_FINALES))
        )
        termino = self.request.GET.get("q", "").strip()
        if termino:
            qs = qs.filter(
                Q(codigo_interno__icontains=termino)
                | Q(marca__icontains=termino)
                | Q(modelo__icontains=termino)
                | Q(ubicacion__icontains=termino)
            )
        tipo = self.request.GET.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class EquipoDetailView(LoginRequiredMixin, DetailView):
    model = Equipo
    template_name = "equipos/detalle.html"
    context_object_name = "equipo"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tickets"] = (
            self.object.tickets.visibles_para(self.request.user)
            .con_relaciones()
            .order_by("-creado_en")[:20]
        )
        return ctx


class EquipoCreateView(SoloAdminMixin, CreateView):
    model = Equipo
    form_class = EquipoForm
    template_name = "equipos/formulario.html"
    success_url = reverse_lazy("equipos:lista")


class EquipoUpdateView(SoloAdminMixin, UpdateView):
    model = Equipo
    form_class = EquipoForm
    template_name = "equipos/formulario.html"
