from rest_framework import serializers
from .models import Rol, Modulo, Operacion, RolesOperaciones, UserOperacionOverride, PerfilUsuario, Prospecto
from authentication.models import User

class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ('id', 'nombre', 'descripcion')

class ModuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modulo
        fields = ('id', 'nombre')

class OperacionSerializer(serializers.ModelSerializer):
    modulo = ModuloSerializer(read_only=True)
    modulo_id = serializers.PrimaryKeyRelatedField(queryset=Modulo.objects.all(), source='modulo', write_only=True)

    class Meta:
        model = Operacion
        fields = ('id', 'nombre', 'modulo', 'modulo_id')

class RolesOperacionesSerializer(serializers.ModelSerializer):
    # read only nested representations
    rol = RolSerializer(read_only=True)
    modulo = ModuloSerializer(read_only=True)
    operacion = OperacionSerializer(read_only=True)

    # write-only PK fields for create/update
    rol_id = serializers.PrimaryKeyRelatedField(queryset=Rol.objects.all(), source='rol', write_only=True)
    modulo_id = serializers.PrimaryKeyRelatedField(queryset=Modulo.objects.all(), source='modulo', write_only=True)
    operacion_id = serializers.PrimaryKeyRelatedField(queryset=Operacion.objects.all(), source='operacion', write_only=True)

    class Meta:
        model = RolesOperaciones
        fields = (
            'id',
            'rol', 'rol_id',
            'modulo', 'modulo_id',
            'operacion', 'operacion_id',
            # 'allow',  <-- eliminado porque el modelo no lo define
        )

class UserOperacionOverrideSerializer(serializers.ModelSerializer):
    # show user basic info + write by id
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    user_display = serializers.SerializerMethodField(read_only=True)

    modulo = ModuloSerializer(read_only=True)
    modulo_id = serializers.PrimaryKeyRelatedField(queryset=Modulo.objects.all(), source='modulo', write_only=True)

    operacion = OperacionSerializer(read_only=True)
    operacion_id = serializers.PrimaryKeyRelatedField(queryset=Operacion.objects.all(), source='operacion', write_only=True)

    class Meta:
        model = UserOperacionOverride
        fields = (
            'id',
            'user', 'user_display',
            'modulo', 'modulo_id',
            'operacion', 'operacion_id',
            'allow',
        )

    def get_user_display(self, obj):
        return {"id": obj.user.id, "username": obj.user.username}

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
            'experiencia_agricola',
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

class ProspectoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prospecto
        fields = '__all__'