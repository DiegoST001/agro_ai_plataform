from django.urls import path
from .views import (
    PublicPlanListView,
    PlanListCreateView, PlanDetailView,
    ParcelaPlanListView, ParcelaPlanCreateView, ParcelaPlanDetailView,
)

urlpatterns = [
    path('planes/public/', PublicPlanListView.as_view(), name='planes-public-list'),
    path('planes/', PlanListCreateView.as_view(), name='planes-list-create'),
    path('planes/<int:pk>/', PlanDetailView.as_view(), name='plan-detail'),
    path('parcelas/<int:parcela_id>/planes/', ParcelaPlanListView.as_view(), name='parcelaplan-list'),
    path('parcelas/<int:parcela_id>/planes/crear/', ParcelaPlanCreateView.as_view(), name='parcelaplan-create'),
    path('parcelas/planes/<int:pk>/', ParcelaPlanDetailView.as_view(), name='parcelaplan-detail'),
]