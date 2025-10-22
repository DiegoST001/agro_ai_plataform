from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Parcela, Cultivo, Variedad

User = get_user_model()

class MinimalUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class CultivoSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cultivo
        fields = ('id', 'nombre')

class VariedadSimpleSerializer(serializers.ModelSerializer):
    cultivo = CultivoSimpleSerializer(read_only=True)

    class Meta:
        model = Variedad
        fields = ('id', 'nombre', 'cultivo')

class CultivoWithVariedadSerializer(serializers.ModelSerializer):
    variedad = serializers.SerializerMethodField()

    class Meta:
        model = Cultivo
        fields = ('id', 'nombre', 'variedad')

    def get_variedad(self, obj):
        # obj: Cultivo, self.instance: Parcela
        parcela = self.context.get('parcela')
        if parcela and parcela.variedad and parcela.variedad.cultivo_id == obj.id:
            return VariedadSimpleSerializer(parcela.variedad).data
        return None

class ParcelaAdminListSerializer(serializers.ModelSerializer):
    usuario = MinimalUserSerializer(read_only=True)
    cultivo = serializers.SerializerMethodField()
    nodos_maestros_count = serializers.IntegerField(read_only=True)
    nodos_secundarios_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Parcela
        fields = (
            'id', 'nombre', 'ubicacion', 'tamano_hectareas', 'latitud', 'longitud',
            'altitud', 'created_at', 'updated_at',
            'usuario', 'cultivo', 'nodos_maestros_count', 'nodos_secundarios_count',
        )

    def get_cultivo(self, obj):
        serializer = CultivoWithVariedadSerializer(
            obj.cultivo,
            context={'parcela': obj}
        )
        return serializer.data

class ParcelaOwnerListSerializer(serializers.ModelSerializer):
    cultivo = serializers.SerializerMethodField()
    nodos_maestros_count = serializers.IntegerField(read_only=True)
    nodos_secundarios_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Parcela
        fields = (
            'id', 'nombre', 'ubicacion', 'tamano_hectareas', 'latitud', 'longitud',
            'altitud', 'created_at', 'updated_at',
            'cultivo', 'nodos_maestros_count', 'nodos_secundarios_count',
        )

    def get_cultivo(self, obj):
        serializer = CultivoWithVariedadSerializer(
            obj.cultivo,
            context={'parcela': obj}
        )
        return serializer.data

# Los serializers de creación/actualización no cambian
class ParcelaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parcela
        fields = (
            'nombre', 'ubicacion', 'tamano_hectareas',
            'latitud', 'longitud', 'altitud', 'cultivo', 'variedad',
        )
        extra_kwargs = {
            'nombre': {'required': True},
            'cultivo': {'required': True},
            'variedad': {'required': True},
        }

class ParcelaUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parcela
        fields = (
            'id', 'nombre', 'ubicacion', 'tamano_hectareas',
            'latitud', 'longitud', 'altitud', 'cultivo', 'variedad',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

class CultivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cultivo
        fields = ('id', 'nombre')
        read_only_fields = ('id',)

class VariedadSerializer(serializers.ModelSerializer):
    # cultivo será asignado por la vista (read_only) cuando se cree vía /cultivos/<id>/variedades/
    cultivo = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Variedad
        fields = ('id', 'cultivo', 'nombre')
        read_only_fields = ('id',)

    def validate(self, data):
        # obtener cultivo a validar: desde contexto (la vista pasa 'cultivo' si disponible) o desde la instancia
        cultivo = self.context.get('cultivo') or getattr(self.instance, 'cultivo', None)
        nombre = data.get('nombre') or getattr(self.instance, 'nombre', None)
        if cultivo and nombre:
            qs = Variedad.objects.filter(cultivo=cultivo, nombre__iexact=nombre)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Ya existe esa variedad para el cultivo indicado.")
        return data