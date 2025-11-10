from rest_framework import serializers
from .models import AIIntegration

class AIIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIIntegration
        fields = "__all__"

# Añadir (faltaba)
class ChatRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField()
    parcela_id = serializers.IntegerField(required=False)