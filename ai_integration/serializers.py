from rest_framework import serializers
from .models import AIIntegration

class AIIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIIntegration
        fields = "__all__"
        extra_kwargs = {
            # Si existen, se ocultan en respuestas y solo se aceptan por escritura
            "api_key": {"write_only": True},
            "secret": {"write_only": True},
            "access_token": {"write_only": True},
        }