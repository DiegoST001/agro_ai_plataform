from rest_framework import serializers
from .models import Task

class TaskSerializer(serializers.ModelSerializer):
    parcela_id = serializers.IntegerField(source='parcela.id', read_only=True)
    decision = serializers.CharField(read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'parcela_id', 'tipo', 'descripcion',
            'fecha_programada', 'estado', 'origen', 'decision', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'decision')