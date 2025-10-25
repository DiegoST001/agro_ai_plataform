from django.urls import path
from .views import (
    ParcelaListCreateView, ParcelaDetailView,
    CultivoListCreateView, CultivoDetailView,
    VariedadListCreateView, VariedadDetailView,
    EtapaListCreateView, EtapaDetailView,
    ReglaPorEtapaListCreateView, ReglaPorEtapaDetailView,
)

urlpatterns = [
    path('parcelas/', ParcelaListCreateView.as_view(), name='parcelas-list-create'),
    path('parcelas/<int:pk>/', ParcelaDetailView.as_view(), name='parcelas-detail'),
    path('cultivos/', CultivoListCreateView.as_view(), name='cultivos-list-create'),
    path('cultivos/<int:pk>/', CultivoDetailView.as_view(), name='cultivos-detail'),

    # crear/listar variedades por cultivo
    path('cultivos/<int:cultivo_id>/variedades/', VariedadListCreateView.as_view(), name='cultivo-variedades-list-create'),

    # rutas generales de variedades
    path('variedades/', VariedadListCreateView.as_view(), name='variedades-list-create'),
    path('variedades/<int:pk>/', VariedadDetailView.as_view(), name='variedades-detail'),

    # nuevas rutas de etapas
    path('variedades/<int:variedad_id>/etapas/', EtapaListCreateView.as_view(), name='variedad-etapas-list-create'),
    path('etapas/', EtapaListCreateView.as_view(), name='etapas-list-create'),
    path('etapas/<int:pk>/', EtapaDetailView.as_view(), name='etapas-detail'),

    # Reglas por etapa
    path('etapas/<int:etapa_id>/reglas/', ReglaPorEtapaListCreateView.as_view(), name='etapa-reglas-list-create'),
    path('reglas/', ReglaPorEtapaListCreateView.as_view(), name='reglas-list-create'),
    path('reglas/<int:pk>/', ReglaPorEtapaDetailView.as_view(), name='reglas-detail'),
]