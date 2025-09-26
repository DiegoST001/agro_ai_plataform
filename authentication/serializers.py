from django.db import transaction
from rest_framework import serializers
from .models import User
from users.models import PerfilUsuario, Rol

class UserRegisterSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    # perfil
    nombres = serializers.CharField(required=False, allow_blank=True)
    apellidos = serializers.CharField(required=False, allow_blank=True)
    telefono = serializers.CharField(required=False, allow_blank=True)
    dni = serializers.CharField(required=False, allow_blank=True)
    fecha_nacimiento = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        if User.objects.filter(username__iexact=attrs['username']).exists():
            raise serializers.ValidationError({'username': 'Ya existe un usuario con este nombre.'})
        if User.objects.filter(email__iexact=attrs['email']).exists():
            raise serializers.ValidationError({'email': 'Ya existe un usuario con este email.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        rol_agricultor = Rol.objects.get(nombre__iexact='agricultor')
        password = validated_data.pop('password')
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            rol=rol_agricultor,
            is_active=True
        )
        user.set_password(password)
        user.save()
        PerfilUsuario.objects.get_or_create(
            usuario=user,
            defaults={
                'nombres': validated_data.get('nombres', ''),
                'apellidos': validated_data.get('apellidos', ''),
                'telefono': validated_data.get('telefono', ''),
                'dni': validated_data.get('dni', ''),
                'fecha_nacimiento': validated_data.get('fecha_nacimiento', None),
            },
        )
        return {'user_id': user.id, 'username': user.username, 'email': user.email}

class PerfilUsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerfilUsuario
        fields = ('nombres', 'apellidos', 'telefono', 'dni', 'fecha_nacimiento')

class AccountSerializer(serializers.ModelSerializer):
    rol = serializers.CharField(source='rol.nombre', read_only=True)
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'rol', 'profile')

    def get_profile(self, obj):
        perfil, _ = PerfilUsuario.objects.get_or_create(usuario=obj)
        return PerfilUsuarioSerializer(perfil).data

class PerfilUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerfilUsuario
        fields = ('nombres', 'apellidos', 'telefono', 'dni', 'fecha_nacimiento')