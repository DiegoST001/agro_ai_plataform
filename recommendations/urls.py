from django.urls import path
from .views import (
    RecommendationListView,
    RecommendationByParcelaListCreateView,
    RecommendationDetailView,
)

urlpatterns = [
    path('recomendaciones/', RecommendationListView.as_view(), name='recomendaciones-list'),
    path('parcelas/<int:parcela_id>/recomendaciones/', RecommendationByParcelaListCreateView.as_view(), name='recomendaciones-by-parcela'),
    path('recomendaciones/<int:pk>/', RecommendationDetailView.as_view(), name='recomendacion-detail'),
]