from datetime import date
from django.db import transaction
from rest_framework import serializers
from .models import Parcela
from plans.models import Plan, ParcelaPlan
from authentication.models import User
from nodes.models import Node, NodoSecundario
from nodes.serializers import NodeSerializer, NodoSecundarioSerializer

class ParcelaUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class ParcelaCreateSerializer(serializers.Serializer):
    nombre = serializers.CharField()
    ubicacion = serializers.CharField(required=False, allow_blank=True)
    tamano_hectareas = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    latitud = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    longitud = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    altitud = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    tipo_cultivo = serializers.CharField(required=False, allow_blank=True)
    plan_id = serializers.IntegerField(write_only=True)

    def validate_plan_id(self, value):
        if not Plan.objects.filter(id=value).exists():
            raise serializers.ValidationError('Plan no encontrado.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user
        plan = Plan.objects.get(id=validated_data.pop('plan_id'))
        parcela = Parcela.objects.create(usuario=user, **validated_data)
        ParcelaPlan.objects.create(
            parcela=parcela, plan=plan, fecha_inicio=date.today(), estado='activo'
        )
        return parcela

    def to_representation(self, instance):
        pp = ParcelaPlan.objects.filter(parcela=instance, estado='activo').select_related('plan').first()
        return {'parcela_id': instance.id, 'plan': pp.plan.nombre if pp else None}

class ParcelaListSerializer(serializers.ModelSerializer):
    usuario = ParcelaUserSerializer(read_only=True)
    plan_activo = serializers.SerializerMethodField()
    nodos_maestros = serializers.SerializerMethodField()

    class Meta:
        model = Parcela
        fields = [
            'id', 'nombre', 'ubicacion', 'tamano_hectareas', 'latitud', 'longitud',
            'altitud', 'tipo_cultivo', 'plan_activo', 'created_at', 'updated_at',
            'usuario', 'nodos_maestros'
        ]

    def get_plan_activo(self, obj):
        pp = ParcelaPlan.objects.filter(parcela=obj, estado='activo').select_related('plan').first()
        return pp.plan.nombre if pp else None

    def get_nodos_maestros(self, obj):
        nodos = Node.objects.filter(parcela=obj)
        return [
            {
                **NodeSerializer(nodo).data,
                'nodos_secundarios': NodoSecundarioSerializer(nodo.secundarios.all(), many=True).data
            }
            for nodo in nodos
        ]

class ParcelaUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parcela
        fields = (
            'nombre', 'ubicacion', 'tamano_hectareas', 'latitud', 'longitud',
            'altitud', 'tipo_cultivo'
        )
        extra_kwargs = {f: {'required': False} for f in fields}

class ParcelaBasicListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parcela
        fields = [
            'id', 'nombre', 'ubicacion', 'tamano_hectareas', 'latitud', 'longitud',
            'altitud', 'tipo_cultivo', 'created_at', 'updated_at'
        ]