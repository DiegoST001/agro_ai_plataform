from django.urls import path
from .views import KPIsView, TimeSeriesView, HistoryView, BrainNodesLatestView

urlpatterns = [
    path('kpis/', KPIsView.as_view(), name='brain-kpis'),
    path('series/', TimeSeriesView.as_view(), name='brain-series'),
    path('history/', HistoryView.as_view(), name='brain-history'),
    path('nodes/latest/', BrainNodesLatestView.as_view(), name='brain-nodes-latest'),
]