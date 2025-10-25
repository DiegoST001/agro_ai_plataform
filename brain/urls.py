from django.urls import path
from .views import KPIsView, TimeSeriesView, HistoryView

urlpatterns = [
    path('kpis/', KPIsView.as_view(), name='brain-kpis'),
    path('series/', TimeSeriesView.as_view(), name='brain-series'),
    path('history/', HistoryView.as_view(), name='brain-history'),
]