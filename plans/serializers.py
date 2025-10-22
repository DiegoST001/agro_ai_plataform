from rest_framework import serializers
from .models import Plan, ParcelaPlan

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            'id', 'nombre', 'descripcion', 'frecuencia_minutos',
            'veces_por_dia', 'horarios_por_defecto', 'limite_lecturas_dia',
            'precio', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')

class ParcelaPlanSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.all(), source='plan', write_only=True
    )
    parcela_id = serializers.IntegerField(source='parcela.id', read_only=True)

    class Meta:
        model = ParcelaPlan
        fields = [
            'id', 'parcela_id', 'plan', 'plan_id', 'fecha_inicio', 'fecha_fin',
            'estado', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')