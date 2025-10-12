from django.urls import path
from parcels.views import (
    AdminParcelaListView,        # Listar todas las parcelas (puedes filtrar por usuario)
    AdminParcelaDetailView,      # Consultar una parcela específica
)
from plans.views import ParcelaPlanDetailView  # Vista para consultar el plan de una parcela
from nodes.views import (
    NodoMasterListView,          # Listar nodos master de una parcela
    NodoSecundarioListView       # Listar nodos secundarios de un nodo master
)

urlpatterns = [
    # Listar parcelas de un usuario (cliente)
    path('users/<int:user_id>/parcelas/', AdminParcelaListView.as_view(), name='admin-user-parcelas'),

    # Consultar una parcela específica de un usuario
    path('users/<int:user_id>/parcelas/<int:parcela_id>/', AdminParcelaDetailView.as_view(), name='admin-user-parcela-detail'),

    # Consultar el plan de una parcela
    path('parcelas/<int:parcela_id>/plan/', ParcelaPlanDetailView.as_view(), name='admin-parcela-plan'),

    # Listar nodos master de una parcela
    # path('parcelas/<int:parcela_id>/nodos-master/', NodoMasterListView.as_view(), name='admin-parcela-nodos-master'),

    # Listar nodos secundarios de un nodo master
    # path('nodos-master/<int:nodo_master_id>/nodos-secundarios/', NodoSecundarioListView.as_view(), name='admin-nodo-master-nodos-secundarios'),
]