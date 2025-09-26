from django.urls import path
from .views import AlertRuleListCreateView, AlertListView

urlpatterns = [
    path('alerts/rules/', AlertRuleListCreateView.as_view(), name='alert-rules'),
    path('alerts/', AlertListView.as_view(), name='alerts-list'),
]