from rest_framework import serializers
from .models import Task
from parcels.models import Parcela

class TaskSerializer(serializers.ModelSerializer):
    # sobrescribimos para evitar la validación automática de ChoiceField
    estado = serializers.CharField(required=False, allow_blank=False)
    parcela_id = serializers.IntegerField(write_only=True, required=False)
    parcela = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Task
        fields = (
            'id', 'parcela_id', 'parcela', 'tipo', 'descripcion',
            'fecha_programada', 'estado', 'origen', 'decision',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'origen', 'decision', 'estado', 'created_at', 'updated_at')

    def get_parcela(self, obj):
        if not obj.parcela_id:
            return None
        return {'id': obj.parcela_id, 'nombre': getattr(obj.parcela, 'nombre', '')}

    def validate_estado(self, value):
        # normalizar sinónimos comunes
        if not isinstance(value, str):
            raise serializers.ValidationError("Estado debe ser una cadena.")
        v = value.strip().lower()
        if v == 'vencido':
            v = 'vencida'
        # comprobar contra las claves válidas definidas en el modelo
        allowed = [k for k, _ in Task.ESTADO_CHOICES]
        if v not in allowed:
            raise serializers.ValidationError(f"Estado inválido. Valores permitidos: {allowed}")
        return v

    def validate(self, attrs):
        # Asegurar que cliente no intente forzar origen/decision incluso si los envía
        attrs.pop('origen', None)
        attrs.pop('decision', None)
        # En creación global debe venir parcela_id, en endpoint por parcela no
        if self.instance is None:
            if 'parcela_id' not in attrs and not self.context.get('parcela_forced'):
                raise serializers.ValidationError({'parcela_id': 'Este campo es requerido en creación global.'})
        return super().validate(attrs)

    def create(self, validated_data):
        validated_data.pop('parcela_id', None)  # ya se asigna en la vista
        return super().create(validated_data)