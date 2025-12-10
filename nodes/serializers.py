import secrets
from datetime import timedelta
from django.utils import timezone
from rest_framework import serializers
from .models import TokenNodo, Node, NodoSecundario
from users.permissions import role_name

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
    token = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Node
        fields = [
            'id', 'codigo', 'parcela', 'lat', 'lng', 'estado', 'bateria',
            'senal', 'last_seen', 'created_at', 'updated_at', 'nodos_secundarios',
            'token',
        ]
        extra_kwargs = {
            'parcela': {'read_only': True},
            'codigo': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
        }

    def get_nodos_secundarios(self, obj):
        secundarios_qs = obj.secundarios.all()
        # Si el contexto pide incluir los secundarios, devolver la lista serializada
        if self.context.get('include_secundarios'):
            return NodoSecundarioSerializer(secundarios_qs, many=True, context=self.context).data
        # Por defecto devolver solo el contador (no null)
        return {'count': secundarios_qs.count()}

    def get_token(self, obj):
        # obtiene el token más reciente válido/en_gracia
        token = obj.tokens.filter(estado__in=['valido','en_gracia']).order_by('-fecha_creacion').first()
        if not token:
            return None
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        # Mostrar key completa solo a admins/superadmin
        if user and role_name(user) in ('superadmin', 'administrador'):
            return token.key
        # para otros mostrar parte (mask)
        return f"{token.key[:8]}...{token.key[-4:]}"

class NodoSecundarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodoSecundario
        fields = ['id', 'codigo', 'maestro', 'estado', 'bateria', 'last_seen', 'created_at', 'updated_at']
        extra_kwargs = {
            'maestro': {'read_only': True},
            'codigo': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
        }
