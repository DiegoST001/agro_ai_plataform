from django.urls import path
from .views import RecommendationByParcelaListView, RecommendationUserListView

urlpatterns = [
    # Solo listar alertas por parcela (el frontend lee las alertas guardadas en el modelo)
    path('parcelas/<int:parcela_id>/alertas/', RecommendationByParcelaListView.as_view(), name='alertas-by-parcela'),
    path('alertas/', RecommendationUserListView.as_view(), name='alertas-user'),
]