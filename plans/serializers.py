from rest_framework import serializers
from .models import Plan

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ('id', 'nombre', 'descripcion', 'frecuencia_minutos', 'precio', 'created_at', 'updated_at')