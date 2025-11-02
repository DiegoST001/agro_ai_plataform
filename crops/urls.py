from django.urls import path
from . import views

urlpatterns = [
    # Cultivos
    path('cultivos/', views.CultivoListCreateView.as_view(), name='cultivos-list-create'),
    path('cultivos/<int:pk>/', views.CultivoDetailView.as_view(), name='cultivos-detail'),

    # Variedades (anidado por cultivo y rutas generales)
    path('cultivos/<int:cultivo_id>/variedades/', views.VariedadListCreateView.as_view(), name='cultivo-variedades-list-create'),
    path('variedades/', views.VariedadListCreateView.as_view(), name='variedades-list-create'),
    path('variedades/<int:pk>/', views.VariedadDetailView.as_view(), name='variedades-detail'),

    # Etapas (anidado por variedad y rutas generales)
    path('variedades/<int:variedad_id>/etapas/', views.EtapaListCreateView.as_view(), name='variedad-etapas-list-create'),
    path('etapas/', views.EtapaListCreateView.as_view(), name='etapas-list'),
    path('etapas/<int:pk>/', views.EtapaDetailView.as_view(), name='etapas-detail'),

    # Reglas por etapa (anidado y global)
    path('etapas/<int:etapa_id>/reglas/', views.EtapaReglaListCreateView.as_view(), name='etapa-reglas-list-create'),
    path('reglas/', views.ReglaListView.as_view(), name='reglas-list'),
    path('reglas/<int:pk>/', views.ReglaDetailView.as_view(), name='reglas-detail'),
]