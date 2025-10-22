from django.urls import path
from .views import (
    ParcelaListCreateView, ParcelaDetailView,
    CultivoListCreateView, CultivoDetailView,
    VariedadListCreateView, VariedadDetailView,
)

urlpatterns = [
    path('parcelas/', ParcelaListCreateView.as_view(), name='parcelas-list-create'),
    path('parcelas/<int:pk>/', ParcelaDetailView.as_view(), name='parcelas-detail'),
    path('cultivos/', CultivoListCreateView.as_view(), name='cultivos-list-create'),
    path('cultivos/<int:pk>/', CultivoDetailView.as_view(), name='cultivos-detail'),

    # nueva ruta: crear/listar variedades por cultivo (mejor UX para frontend)
    path('cultivos/<int:cultivo_id>/variedades/', VariedadListCreateView.as_view(), name='cultivo-variedades-list-create'),

    # rutas generales de variedades (mantener compatibilidad)
    path('variedades/', VariedadListCreateView.as_view(), name='variedades-list-create'),
    path('variedades/<int:pk>/', VariedadDetailView.as_view(), name='variedades-detail'),
]