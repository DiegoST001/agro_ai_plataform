from django.urls import path, re_path
from .views import (
    NodeIngestView,
    NodoMasterListView, NodoSecundarioListView,
    NodeCreateView, NodeUpdateView, NodoSecundarioCreateView,
    NodeListView, NodeDetailView, NodeDeleteView,
    NodoSecundarioDeleteView, NodoSecundarioListAllView,
    NodoSecundarioDetailView, NodoSecundarioUpdateView,
)

urlpatterns = [
    path('nodes/ingest/', NodeIngestView.as_view(), name='nodes-ingest'),

    path('parcelas/<int:parcela_id>/nodos/', NodoMasterListView.as_view(), name='nodos-master-list'),
    path('parcelas/<int:parcela_id>/nodos/create/', NodeCreateView.as_view(), name='nodos-master-create'),
    re_path(r'^parcelas/(?P<parcela_id>\d+)/nodos/(?P<pk>\d+)/?$', NodeDetailView.as_view(), name='nodos-master-detail'),

    path('nodos/', NodeListView.as_view(), name='nodos-list'),
    re_path(r'^nodos/(?P<pk>\d+)/?$', NodeDetailView.as_view(), name='nodos-detail'),
    re_path(r'^nodos/(?P<pk>\d+)/update/?$', NodeUpdateView.as_view(), name='nodos-update'),
    re_path(r'^nodos/(?P<pk>\d+)/delete/?$', NodeDeleteView.as_view(), name='nodos-delete'),
    re_path(r'^nodos/(?P<nodo_master_id>\d+)/secundarios/?$', NodoSecundarioListView.as_view(), name='nodos-secundarios-list'),
    re_path(r'^nodos/(?P<nodo_master_id>\d+)/secundarios/create/?$', NodoSecundarioCreateView.as_view(), name='nodos-secundarios-create'),
    re_path(r'^secundarios/(?P<pk>\d+)/?$', NodoSecundarioDetailView.as_view(), name='nodos-secundarios-detail'),
    re_path(r'^secundarios/(?P<pk>\d+)/update/?$', NodoSecundarioUpdateView.as_view(), name='nodos-secundarios-update'),
    re_path(r'^secundarios/(?P<pk>\d+)/delete/?$', NodoSecundarioDeleteView.as_view(), name='nodos-secundarios-delete'),

    path('secundarios/', NodoSecundarioListAllView.as_view(), name='nodos-secundarios-all'),
]