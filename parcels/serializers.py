from django.contrib.auth import get_user_model
from rest_framework import serializers
from typing import Any, Optional, Dict

from .models import Parcela, Ciclo, ParcelaImage
from crops.models import Cultivo, Variedad, Etapa
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
import cloudinary.uploader

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

    @extend_schema_field(OpenApiTypes.STR)
    def get_cultivo(self, obj):
        return self._to_basic(obj.cultivo)

    def get_variedad(self, obj):
        return self._to_basic(obj.variedad)

    def get_etapa_actual(self, obj):
        return self._to_basic(obj.etapa_actual)


class ParcelaImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParcelaImage
        fields = ('id', 'image_url', 'public_id', 'filename', 'uploaded_by', 'created_at')
        read_only_fields = ('id', 'image_url', 'public_id', 'filename', 'uploaded_by', 'created_at')


# -----------------------
# Parcela serializers
# -----------------------
class ParcelaCreateSerializer(serializers.ModelSerializer):
    usuario = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    ciclo = CicloCreateSerializer(required=False, write_only=True)

    class Meta:
        model = Parcela
        fields = ('id', 'usuario', 'nombre', 'ubicacion', 'tamano_hectareas', 'latitud', 'longitud', 'altitud', 'ciclo', 'imagen_url', 'imagen_public_id')
        read_only_fields = ('id', 'imagen_url', 'imagen_public_id')

    def create(self, validated_data):
        # crea la parcela normalmente
        ciclo_data = validated_data.pop('ciclo', None)
        parcela = super().create(validated_data)
        if ciclo_data:
            Ciclo.objects.create(parcela=parcela, **ciclo_data)

        # Si se subió un fichero 'imagen' en la request (multipart/form-data), subirlo a Cloudinary y guardar URL
        request = self.context.get('request')
        if request and hasattr(request, 'FILES'):
            file_obj = request.FILES.get('imagen')
            if file_obj:
                try:
                    res = cloudinary.uploader.upload(
                        file_obj,
                        folder=f"agro_ai/parcels_preview/{parcela.id}",
                        resource_type="image",
                        use_filename=True,
                        unique_filename=True
                    )
                    parcela.imagen_url = res.get('secure_url')
                    parcela.imagen_public_id = res.get('public_id')
                    parcela.save(update_fields=['imagen_url', 'imagen_public_id', 'updated_at'])
                except Exception:
                    # no romper la creación por fallo en upload; puedes loggear aquí
                    pass

        return parcela

class ParcelaReadSerializer(serializers.ModelSerializer):
    usuario = MinimalUserSerializer(read_only=True)
    ciclos = CicloReadSerializer(many=True, read_only=True)
    images = ParcelaImageSerializer(many=True, read_only=True)

    class Meta:
        model = Parcela
        fields = ('id', 'usuario', 'nombre', 'ubicacion', 'tamano_hectareas', 'latitud', 'longitud', 'altitud', 'ciclos', 'images', 'imagen_url')


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