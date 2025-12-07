from rest_framework import serializers
from .models import ChatMessage, CropData


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer para mensajes de chat"""
    class Meta:
        model = ChatMessage
        fields = ['id', 'username', 'message', 'is_user', 'timestamp']
        read_only_fields = ['id', 'timestamp']


class ChatRequestSerializer(serializers.Serializer):
    """Serializer para la petición de chat desde el frontend"""
    message = serializers.CharField(required=True, help_text="Mensaje del usuario")
    username = serializers.CharField(required=False, default='', help_text="Nombre del usuario")


class ChatResponseSerializer(serializers.Serializer):
    """Serializer para la respuesta del chatbot"""
    response = serializers.CharField(help_text="Respuesta del bot")
    crop_data = serializers.DictField(required=False, help_text="Datos del cultivo si están disponibles")
    tasks_created = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Lista de tareas creadas automáticamente"
    )


class CropDataSerializer(serializers.ModelSerializer):
    """Serializer para datos de cultivo"""
    class Meta:
        model = CropData
        fields = [
            'id', 'temperature_air', 'humidity_air', 'humidity_soil',
            'conductivity_ec', 'temperature_soil', 'solar_radiation',
            'pest_risk', 'last_updated'
        ]
        read_only_fields = ['id', 'last_updated']
