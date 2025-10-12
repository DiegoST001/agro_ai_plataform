from rest_framework import serializers
from .models import AIIntegration

class AIIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIIntegration
        fields = "__all__"