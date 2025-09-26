from django.urls import path
from .views import SensorListView, SensorReadingsView

urlpatterns = [
    path('sensors/', SensorListView.as_view(), name='sensors-list'),
    path('sensors/<int:sensor_id>/readings/', SensorReadingsView.as_view(), name='sensors-readings'),
]