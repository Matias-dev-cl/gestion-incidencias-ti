from django.urls import path

from . import views

app_name = "equipos"

urlpatterns = [
    path("", views.EquipoListView.as_view(), name="lista"),
    path("nuevo/", views.EquipoCreateView.as_view(), name="crear"),
    path("<int:pk>/", views.EquipoDetailView.as_view(), name="detalle"),
    path("<int:pk>/editar/", views.EquipoUpdateView.as_view(), name="editar"),
]
