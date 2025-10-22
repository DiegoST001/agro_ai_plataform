from django.urls import path
from .views import (
    TaskListCreateView, TaskDetailView, TaskByParcelaListCreateView
)

urlpatterns = [
    path('tareas/', TaskListCreateView.as_view(), name='tareas-list-create'),
    path('tareas/<int:pk>/', TaskDetailView.as_view(), name='tareas-detail'),
    path('parcelas/<int:parcela_id>/tareas/', TaskByParcelaListCreateView.as_view(), name='tareas-by-parcela'),
]