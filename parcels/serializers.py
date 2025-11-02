from django.contrib.auth import get_user_model
from rest_framework import serializers
from typing import Any, Optional, Dict

from .models import Parcela, Ciclo
from crops.models import Cultivo, Variedad, Etapa

User = get_user_model()


class MinimalUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')


# -----------------------
# Ciclo serializers
# -----------------------
class CicloCreateSerializer(serializers.ModelSerializer):
    cultivo = serializers.PrimaryKeyRelatedField(queryset=Cultivo.objects.all(), required=False, allow_null=True)
    variedad = serializers.PrimaryKeyRelatedField(queryset=Variedad.objects.all(), required=False, allow_null=True)
    etapa_actual = serializers.PrimaryKeyRelatedField(queryset=Etapa.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Ciclo
        fields = ('cultivo', 'variedad', 'etapa_actual', 'etapa_inicio')

    def validate(self, attrs):
        etapa = attrs.get('etapa_actual')
        variedad = attrs.get('variedad')
        if etapa and variedad and etapa.variedad_id != variedad.id:
            raise serializers.ValidationError("La 'etapa_actual' debe pertenecer a la 'variedad' indicada.")
        return attrs


class CicloReadSerializer(serializers.ModelSerializer):
    cultivo = serializers.SerializerMethodField()
    variedad = serializers.SerializerMethodField()
    etapa_actual = serializers.SerializerMethodField()

    class Meta:
        model = Ciclo
        fields = ('id', 'cultivo', 'variedad', 'etapa_actual', 'etapa_inicio', 'estado', 'fecha_cierre')

    def _to_basic(self, obj):
        if not obj:
            return None
        return {'id': obj.id, 'nombre': getattr(obj, 'nombre', str(obj))}

    def get_cultivo(self, obj):
        return self._to_basic(obj.cultivo)

    def get_variedad(self, obj):
        return self._to_basic(obj.variedad)

    def get_etapa_actual(self, obj):
        return self._to_basic(obj.etapa_actual)


# -----------------------
# Parcela serializers
# -----------------------
class ParcelaCreateSerializer(serializers.ModelSerializer):
    ciclo = CicloCreateSerializer(required=False, write_only=True)

    class Meta:
        model = Parcela
        fields = ('id', 'usuario', 'nombre', 'ubicacion', 'tamano_hectareas', 'latitud', 'longitud', 'altitud', 'ciclo')
        read_only_fields = ('id',)

    def create(self, validated_data):
        ciclo_data = validated_data.pop('ciclo', None)
        parcela = super().create(validated_data)
        if ciclo_data:
            Ciclo.objects.create(parcela=parcela, **ciclo_data)
        return parcela


class ParcelaReadSerializer(serializers.ModelSerializer):
    usuario = MinimalUserSerializer(read_only=True)
    ciclos = CicloReadSerializer(many=True, read_only=True)

    class Meta:
        model = Parcela
        fields = ('id', 'usuario', 'nombre', 'ubicacion', 'tamano_hectareas', 'latitud', 'longitud', 'altitud', 'ciclos')


class ParcelaUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parcela
        fields = (
            'id', 'nombre', 'ubicacion', 'tamano_hectareas',
            'latitud', 'longitud', 'altitud', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, data):
        # Nota: Parcela ya no almacena variedad/etapa directamente; validaciones relacionadas
        # con etapa/variedad deben hacerse en endpoints de Ciclo.
        return data