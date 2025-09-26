from django.shortcuts import render
from datetime import datetime
from rest_framework import generics, permissions, views, status
from rest_framework.response import Response
from .models import Sensor
from .serializers import SensorSerializer
from .mongo import range_readings
from users.permissions import HasOperationPermission

class SensorListView(generics.ListAPIView):
    serializer_class = SensorSerializer
    filterset_fields = ['parcela','node','tipo']
    search_fields = ['nombre','tipo']
    ordering_fields = ['created_at','nombre']
    ordering = ['-created_at']
    def get_queryset(self):
        return Sensor.objects.filter(parcela__usuario=self.request.user)
    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('sensores', 'ver')]

class SensorReadingsView(views.APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('sensores', 'ver')]
    def get(self, request, sensor_id: int):
        try:
            sensor = Sensor.objects.get(id=sensor_id, parcela__usuario=request.user)
        except Sensor.DoesNotExist:
            return Response({'detail':'Sensor no encontrado'}, status=404)
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        if not (start and end):
            return Response({'detail':'start y end requeridos (ISO8601)'}, status=400)
        data = range_readings(sensor.ext_collection, sensor.ext_sensor_id,
                              datetime.fromisoformat(start), datetime.fromisoformat(end))
        return Response(data, status=200)