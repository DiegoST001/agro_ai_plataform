from django.urls import path
from .views import NodeIngestView

urlpatterns = [
    path('ingest/', NodeIngestView.as_view(), name='nodes-ingest'),
]