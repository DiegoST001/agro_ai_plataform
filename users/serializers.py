from rest_framework import serializers
from .models import Rol, Modulo, Operacion, RolesOperaciones, UserOperacionOverride, PerfilUsuario
from authentication.models import User

class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ('id', 'nombre')

class ModuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modulo
        fields = ('id', 'nombre')

class OperacionSerializer(serializers.ModelSerializer):
    modulo = serializers.PrimaryKeyRelatedField(queryset=Modulo.objects.all())
    class Meta:
        model = Operacion
        fields = ('id', 'nombre', 'modulo')

class RolesOperacionesSerializer(serializers.ModelSerializer):
    rol = serializers.PrimaryKeyRelatedField(queryset=Rol.objects.all())
    modulo = serializers.PrimaryKeyRelatedField(queryset=Modulo.objects.all())
    operacion = serializers.PrimaryKeyRelatedField(queryset=Operacion.objects.all())

    class Meta:
        model = RolesOperaciones
        fields = ('id', 'rol', 'modulo', 'operacion')

class UserRoleUpdateSerializer(serializers.Serializer):
    rol_id = serializers.IntegerField()

    def validate_rol_id(self, value):
        if not Rol.objects.filter(id=value).exists():
            raise serializers.ValidationError('Rol no encontrado.')
        return value

    def update(self, instance: User, validated_data):
        instance.rol_id = validated_data['rol_id']
        instance.save(update_fields=['rol'])
        return instance

class UserOperacionOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserOperacionOverride
        fields = ('id', 'user', 'modulo', 'operacion', 'allow')

class AdminUserListSerializer(serializers.ModelSerializer):
    rol = serializers.CharField(source='rol.nombre', read_only=True)
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'rol', 'is_active', 'date_joined')

class AdminUserUpdateSerializer(serializers.ModelSerializer):
    rol_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ('email', 'is_active', 'rol_id')

    def validate_rol_id(self, value):
        if value is not None and not Rol.objects.filter(id=value).exists():
            raise serializers.ValidationError('Rol no encontrado.')
        return value

    def update(self, instance, validated_data):
        rol_id = validated_data.pop('rol_id', None)
        if rol_id is not None:
            instance.rol_id = rol_id
        return super().update(instance, validated_data)

class PerfilUsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerfilUsuario
        fields = [
            'nombres',
            'apellidos',
            'telefono',
            'dni',
            'fecha_nacimiento',
            'experiencia_agricola'
            # Si quieres incluir foto_perfil, agrégalo aquí
        ]

class UserWithProfileSerializer(serializers.ModelSerializer):
    profile = PerfilUsuarioSerializer(source='perfilusuario', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile']

class UserDetailSerializer(serializers.ModelSerializer):
    rol = serializers.CharField(source='rol.nombre', read_only=True)
    profile = PerfilUsuarioSerializer(source='perfilusuario', read_only=True)
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'is_active', 'rol', 'date_joined', 'profile'
        ]