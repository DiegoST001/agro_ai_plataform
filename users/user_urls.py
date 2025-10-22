from django.urls import path
from .views import (
    PerfilUsuarioView,
    ProspectoListView,
    ProspectoDetailView,
    ProspectoAceptarView,
)

urlpatterns = [
    path('profile/', PerfilUsuarioView.as_view(), name='profile'),
    path('prospectos/', ProspectoListView.as_view(), name='prospecto-list'),
    path('prospectos/<int:pk>/', ProspectoDetailView.as_view(), name='prospecto-detail'),
    path('prospectos/<int:pk>/aceptar/', ProspectoAceptarView.as_view(), name='prospecto-aceptar'),
]