from django.urls import path
from .views import ParcelaListCreateView, ParcelaDetailView, AdminParcelaListView, AdminParcelaDetailView

urlpatterns = [
    path('parcelas/', ParcelaListCreateView.as_view(), name='parcelas-list-create'),  # GET listar, POST crear
    path('parcelas/<int:pk>/', ParcelaDetailView.as_view(), name='parcelas-detail'),  # GET detalle, PUT/PATCH editar
    # Admin parcelas
    path('admin/parcelas/', AdminParcelaListView.as_view(), name='admin-parcelas-list'),
    path('admin/parcelas/<int:pk>/', AdminParcelaDetailView.as_view(), name='admin-parcelas-detail'),
]