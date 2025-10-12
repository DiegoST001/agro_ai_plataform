import secrets
from datetime import timedelta
from django.utils import timezone
from rest_framework import serializers
from .models import TokenNodo, Node, NodoSecundario

class TokenNodoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenNodo
        fields = ('id','nodo','key','fecha_expiracion','estado')
        read_only_fields = ('key',)

    def create(self, validated_data):
        # Generar token seguro
        validated_data['key'] = secrets.token_hex(32)
        
        # Asignar expiración por defecto (30 días) si no viene
        if not validated_data.get('fecha_expiracion'):
            validated_data['fecha_expiracion'] = timezone.now() + timedelta(days=30)
        
        return super().create(validated_data)

class NodeSerializer(serializers.ModelSerializer):
    nodos_secundarios = serializers.SerializerMethodField()

    class Meta:
        model = Node
        fields = [
            'id', 'codigo', 'parcela', 'lat', 'lng', 'estado', 'bateria',
            'senal', 'last_seen', 'created_at', 'updated_at', 'nodos_secundarios'
        ]
        extra_kwargs = {
            'parcela': {'read_only': True},  # <-- Así no se requiere en el body
            'codigo': {'read_only': True},   # El código también es automático
        }

    def get_nodos_secundarios(self, obj):
        # Solo incluir secundarios si el contexto lo pide
        if self.context.get('include_secundarios'):
            secundarios = obj.secundarios.all()
            return NodoSecundarioSerializer(secundarios, many=True).data
        return None

class NodoSecundarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodoSecundario
        fields = ['id', 'codigo', 'maestro', 'estado', 'bateria', 'last_seen', 'created_at', 'updated_at']
        extra_kwargs = {
            'maestro': {'read_only': True},  # <-- Esto soluciona el error
            'codigo': {'read_only': True},   # El código también es automático
        }
