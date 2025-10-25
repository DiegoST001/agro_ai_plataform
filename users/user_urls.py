from django.urls import path
from .views import (
    PerfilUsuarioView,
    ProspectoListView,
    ProspectoDetailView,
    ProspectoAceptarView,
    UsuariosTotalPublicView,
    ProspectoPublicCreateView,
)

urlpatterns = [
    path('profile/', PerfilUsuarioView.as_view(), name='profile'),
    path('prospectos/', ProspectoListView.as_view(), name='prospecto-list'),
    path('prospectos/<int:pk>/', ProspectoDetailView.as_view(), name='prospecto-detail'),
    path('prospectos/<int:pk>/aceptar/', ProspectoAceptarView.as_view(), name='prospecto-aceptar'),
    path('total/public/', UsuariosTotalPublicView.as_view(), name='usuarios-total-public'),
    path('prospectos/public/', ProspectoPublicCreateView.as_view(), name='prospecto-public-create'),  # <-- nueva ruta pública
]