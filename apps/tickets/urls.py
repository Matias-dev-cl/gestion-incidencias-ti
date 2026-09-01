from django.urls import path

from . import views

app_name = "tickets"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("tickets/", views.TicketListView.as_view(), name="lista"),
    path("tickets/nuevo/", views.TicketCreateView.as_view(), name="crear"),
    path("tickets/<int:pk>/", views.TicketDetailView.as_view(), name="detalle"),
    path("tickets/<int:pk>/comentar/", views.ComentarioCreateView.as_view(), name="comentar"),
    path("tickets/<int:pk>/gestionar/", views.GestionTicketView.as_view(), name="gestionar"),
    path("tickets/<int:pk>/tomar/", views.AutoasignarView.as_view(), name="autoasignar"),
    path("tickets/<int:pk>/reabrir/", views.ReabrirView.as_view(), name="reabrir"),
]
