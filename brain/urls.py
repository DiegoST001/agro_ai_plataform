from django.urls import path
from .views import TimeSeriesView, HistoryView, BrainNodesLatestView, BrainKPIsUnifiedView, AuditSeriesView, AuditHistoryView

urlpatterns = [
    path('kpis/', BrainKPIsUnifiedView.as_view(), name='brain-kpis'),
    path('kpis/<int:parcela_id>/', BrainKPIsUnifiedView.as_view(), name='brain-kpis-parcela'),
    path('series/', TimeSeriesView.as_view(), name='brain-series'),
    path('history/', HistoryView.as_view(), name='brain-history'),
    path('nodes/latest/', BrainNodesLatestView.as_view(), name='brain-nodes-latest'),
    path('audit/series/', AuditSeriesView.as_view(), name='brain-audit-series'),
    path('audit/history/', AuditHistoryView.as_view(), name='brain-audit-history'),
]