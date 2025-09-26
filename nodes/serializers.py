import secrets
from rest_framework import serializers
from .models import TokenNodo

class TokenNodoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenNodo
        fields = ('id','nodo','key','fecha_expiracion','estado')
        read_only_fields = ('key',)

    def create(self, validated_data):
        validated_data['key'] = secrets.token_hex(32)
        return super().create(validated_data)