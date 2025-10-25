from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Parcela, Cultivo, Variedad, Etapa, ReglaPorEtapa

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
    etapa = serializers.SerializerMethodField()  # agregado
    nodos_maestros_count = serializers.IntegerField(read_only=True)
    nodos_secundarios_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Parcela
        fields = (
            'id', 'nombre', 'ubicacion', 'tamano_hectareas', 'latitud', 'longitud',
            'altitud', 'created_at', 'updated_at',
            'usuario', 'cultivo', 'etapa', 'nodos_maestros_count', 'nodos_secundarios_count',
        )

    def get_cultivo(self, obj):
        serializer = CultivoWithVariedadSerializer(
            obj.cultivo,
            context={'parcela': obj}
        )
        return serializer.data

    def get_etapa(self, obj):
        etapa = getattr(obj, 'etapa_actual', None)
        if not etapa:
            return None
        return {'id': etapa.id, 'nombre': etapa.nombre, 'inicio': obj.etapa_inicio}

class ParcelaOwnerListSerializer(serializers.ModelSerializer):
    cultivo = serializers.SerializerMethodField()
    etapa = serializers.SerializerMethodField()  # agregado
    nodos_maestros_count = serializers.IntegerField(read_only=True)
    nodos_secundarios_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Parcela
        fields = (
            'id', 'nombre', 'ubicacion', 'tamano_hectareas', 'latitud', 'longitud',
            'altitud', 'created_at', 'updated_at',
            'cultivo', 'etapa', 'nodos_maestros_count', 'nodos_secundarios_count',
        )

    def get_cultivo(self, obj):
        serializer = CultivoWithVariedadSerializer(
            obj.cultivo,
            context={'parcela': obj}
        )
        return serializer.data

    def get_etapa(self, obj):
        etapa = getattr(obj, 'etapa_actual', None)
        if not etapa:
            return None
        return {'id': etapa.id, 'nombre': etapa.nombre, 'inicio': obj.etapa_inicio}

# Los serializers de creación/actualización no cambian
class ParcelaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parcela
        fields = (
            'nombre', 'ubicacion', 'tamano_hectareas',
            'latitud', 'longitud', 'altitud', 'cultivo', 'variedad',
            'etapa_actual', 'etapa_inicio',  # añadidos
        )
        extra_kwargs = {
            'nombre': {'required': True},
            'cultivo': {'required': True},
            'variedad': {'required': True},
        }

    def validate(self, data):
        etapa = data.get('etapa_actual')
        variedad = data.get('variedad')
        from rest_framework.exceptions import ValidationError
        if etapa:
            if not variedad:
                raise ValidationError({"variedad": "Proporciona 'variedad' si indicas 'etapa_actual'."})
            if etapa.variedad_id != variedad.id:
                raise ValidationError({"etapa_actual": "La etapa no pertenece a la variedad indicada."})
            if not getattr(etapa, 'activo', True):
                raise ValidationError({"etapa_actual": "La etapa seleccionada está inactiva."})
        return data

class ParcelaUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parcela
        fields = (
            'id', 'nombre', 'ubicacion', 'tamano_hectareas',
            'latitud', 'longitud', 'altitud', 'cultivo', 'variedad',
            'etapa_actual', 'etapa_inicio', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, data):
        etapa = data.get('etapa_actual')
        variedad = data.get('variedad') or getattr(self.instance, 'variedad', None)
        from rest_framework.exceptions import ValidationError
        if etapa:
            if not variedad:
                raise ValidationError({"variedad": "No hay variedad asociada; provee 'variedad' o no especifiques etapa_actual."})
            if etapa.variedad_id != (variedad.id if hasattr(variedad, 'id') else variedad):
                raise ValidationError({"etapa_actual": "La etapa no pertenece a la variedad indicada."})
            if not getattr(etapa, 'activo', True):
                raise ValidationError({"etapa_actual": "La etapa seleccionada está inactiva."})
        return data

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

class EtapaSerializer(serializers.ModelSerializer):
    # variedad será asignada por la vista al crear vía /variedades/<id>/etapas/
    variedad = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Etapa
        fields = ('id', 'variedad', 'nombre', 'orden', 'descripcion', 'duracion_estimada_dias', 'activo')  # agregado 'activo'
        read_only_fields = ('id',)

    def validate(self, data):
        # validar unicidad de nombre por variedad (la vista pasa 'variedad' en el contexto)
        variedad = self.context.get('variedad') or getattr(self.instance, 'variedad', None)
        nombre = data.get('nombre') or getattr(self.instance, 'nombre', None)
        if variedad and nombre:
            qs = Etapa.objects.filter(variedad=variedad, nombre__iexact=nombre)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Ya existe esa etapa para la variedad indicada.")
        return data

class ReglaPorEtapaSerializer(serializers.ModelSerializer):
    etapa = serializers.PrimaryKeyRelatedField(queryset=Etapa.objects.all())
    created_by = MinimalUserSerializer(read_only=True)

    class Meta:
        model = ReglaPorEtapa
        fields = (
            'id','etapa','parametro','minimo','maximo',
            'accion_si_menor','accion_si_mayor','activo','prioridad',
            'effective_from','effective_to','created_by','created_at','updated_at'
        )
        read_only_fields = ('id','created_by','created_at','updated_at')

    def validate(self, data):
        minimo = data.get('minimo', getattr(self.instance, 'minimo', None))
        maximo = data.get('maximo', getattr(self.instance, 'maximo', None))
        if minimo is not None and maximo is not None and minimo > maximo:
            raise serializers.ValidationError("El campo 'minimo' no puede ser mayor que 'maximo'.")
        ef_from = data.get('effective_from', getattr(self.instance, 'effective_from', None))
        ef_to = data.get('effective_to', getattr(self.instance, 'effective_to', None))
        if ef_from and ef_to and ef_from > ef_to:
            raise serializers.ValidationError("effective_from no puede ser posterior a effective_to.")
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['created_by'] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)