from django.urls import path
from .views import (
    NodeIngestView,
    NodoMasterListView,
    NodoSecundarioListView,
    NodeCreateView,
    NodeUpdateView,
    NodoSecundarioCreateView,
    NodeListView,
    NodeDetailView,
)

urlpatterns = [
    path('ingest/', NodeIngestView.as_view(), name='nodes-ingest'),
    path('parcelas/<int:parcela_id>/nodos-master/', NodoMasterListView.as_view(), name='parcela-nodos-master'),
    path('nodos-master/<int:nodo_master_id>/nodos-secundarios/', NodoSecundarioListView.as_view(), name='nodo-master-nodos-secundarios'),
    path('parcelas/<int:parcela_id>/nodos-master/add/', NodeCreateView.as_view(), name='add-nodo-master'),
    path('nodos-master/<int:pk>/edit/', NodeUpdateView.as_view(), name='edit-nodo-master'),
    path('nodos-master/<int:nodo_master_id>/nodos-secundarios/add/', NodoSecundarioCreateView.as_view(), name='add-nodo-secundario'),
    path('nodos-master/', NodeListView.as_view(), name='nodos-master-list'),
    path('nodos-master/<int:pk>/', NodeDetailView.as_view(), name='nodo-master-detail'),
]