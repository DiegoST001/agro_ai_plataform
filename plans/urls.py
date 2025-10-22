from django.urls import path
from .views import (
    PlanListCreateView, PlanDetailView,
    ParcelaPlanListView, ParcelaPlanCreateView, ParcelaPlanDetailView,
)

urlpatterns = [
    # Plans
    path('planes/', PlanListCreateView.as_view(), name='planes-list-create'),
    path('planes/<int:pk>/', PlanDetailView.as_view(), name='plan-detail'),
    # ParcelaPlan / suscripciones
    path('parcelas/<int:parcela_id>/planes/', ParcelaPlanListView.as_view(), name='parcelaplan-list'),
    path('parcelas/<int:parcela_id>/planes/crear/', ParcelaPlanCreateView.as_view(), name='parcelaplan-create'),
    path('parcelas/planes/<int:pk>/', ParcelaPlanDetailView.as_view(), name='parcelaplan-detail'),
]