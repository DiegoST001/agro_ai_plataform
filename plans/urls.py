from django.urls import path
from .views import PlanListView, ParcelaChangePlanView

urlpatterns = [
    path('planes/', PlanListView.as_view(), name='planes-list'),
    path('parcelas/<int:parcela_id>/cambiar-plan/', ParcelaChangePlanView.as_view(), name='parcela-cambiar-plan'),
]