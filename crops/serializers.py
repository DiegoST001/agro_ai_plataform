from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Cultivo, Variedad, Etapa, ReglaPorEtapa

User = get_user_model()


class MinimalUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')


class CultivoSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cultivo
        fields = ('id', 'nombre')


class CultivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cultivo
        fields = ('id', 'nombre', 'descripcion')
        read_only_fields = ('id',)


class EtapaSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Etapa
        fields = ('id', 'nombre', 'orden', 'duracion_estimada_dias', 'activo')


class EtapaSerializer(serializers.ModelSerializer):
    # variedad se debe proporcionar desde la vista/contexto al crear (read_only aquí)
    variedad = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Etapa
        fields = ('id', 'variedad', 'nombre', 'orden', 'descripcion', 'duracion_estimada_dias', 'activo')
        read_only_fields = ('id',)

    def validate(self, data):
        variedad = self.context.get('variedad') or getattr(self.instance, 'variedad', None)
        nombre = data.get('nombre') or getattr(self.instance, 'nombre', None)
        if variedad and nombre:
            qs = Etapa.objects.filter(variedad=variedad, nombre__iexact=nombre)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Ya existe esa etapa para la variedad indicada.")
        return data


class VariedadSimpleSerializer(serializers.ModelSerializer):
    cultivo = CultivoSimpleSerializer(read_only=True)

    class Meta:
        model = Variedad
        fields = ('id', 'nombre', 'cultivo')


class VariedadNestedSerializer(serializers.ModelSerializer):
    etapas = EtapaSimpleSerializer(many=True, read_only=True)

    class Meta:
        model = Variedad
        fields = ('id', 'nombre', 'descripcion', 'etapas')


class VariedadSerializer(serializers.ModelSerializer):
    # cultivo será asignado por la vista (read_only aquí)
    cultivo = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Variedad
        fields = ('id', 'cultivo', 'nombre', 'descripcion')
        read_only_fields = ('id',)

    def validate(self, data):
        cultivo = self.context.get('cultivo') or getattr(self.instance, 'cultivo', None)
        nombre = data.get('nombre') or getattr(self.instance, 'nombre', None)
        if cultivo and nombre:
            qs = Variedad.objects.filter(cultivo=cultivo, nombre__iexact=nombre)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Ya existe esa variedad para el cultivo indicado.")
        return data


class ReglaPorEtapaSerializer(serializers.ModelSerializer):
    etapa = serializers.PrimaryKeyRelatedField(queryset=Etapa.objects.all())
    created_by = MinimalUserSerializer(read_only=True)

    class Meta:
        model = ReglaPorEtapa
        fields = (
            'id', 'etapa', 'parametro', 'minimo', 'maximo',
            'accion_si_menor', 'accion_si_mayor', 'activo', 'prioridad',
            'effective_from', 'effective_to', 'created_by', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')

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
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data)