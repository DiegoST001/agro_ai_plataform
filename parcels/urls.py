from django.urls import path
from . import views

app_name = 'parcels'  # <-- añadido para namespacing

urlpatterns = [
    # Parcelas
    path('parcelas/', views.ParcelaListCreateView.as_view(), name='parcelas-list-create'),
    path('parcelas/crear_mia/', views.ParcelaCreateOwnView.as_view(), name='parcelas-create-own'),
    path('parcelas/<int:pk>/', views.ParcelaDetailView.as_view(), name='parcelas-detail'),

    # Ciclos (por parcela)
    path('parcelas/<int:parcela_id>/ciclos/', views.ParcelaCicloListCreateView.as_view(), name='parcela-ciclos-list-create'),
    path('ciclos/<int:pk>/', views.CicloDetailView.as_view(), name='ciclo-detail'),
    path('ciclos/<int:pk>/avanzar_etapa/', views.CicloAdvanceEtapaView.as_view(), name='ciclo-avanzar-etapa'),
    path('ciclos/<int:pk>/cerrar/', views.CicloCloseView.as_view(), name='ciclo-cerrar'),

    # Advance active ciclo (no PK required) — usa request.user; admin puede pasar ?parcela_id=
    # path('ciclos/avanzar_activo/', views.CicloAdvanceActiveView.as_view, name='ciclo-avanzar-activo'),
]