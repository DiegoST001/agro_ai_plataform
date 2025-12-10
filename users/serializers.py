from rest_framework import serializers
from .models import Rol, Modulo, Operacion, RolesOperaciones, UserOperacionOverride, PerfilUsuario, Prospecto
from authentication.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
UserModel = get_user_model()

class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ('id', 'nombre', 'descripcion')

class ModuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modulo
        fields = ('id', 'nombre', 'descripcion')

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

class AdminUserCreateSerializer(serializers.ModelSerializer):
    # Crear usuario: username, email, password; rol opcional (rol_id)
    rol_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'rol_id', 'is_active')

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('Username ya existe.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Correo ya existe.')
        return value

    def validate_rol_id(self, value):
        if value is not None and not Rol.objects.filter(id=value).exists():
            raise serializers.ValidationError('Rol no encontrado.')
        return value

    def create(self, validated_data):
        rol_id = validated_data.pop('rol_id', None)
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data, password=password)
        if rol_id is not None:
            user.rol_id = rol_id
            user.save(update_fields=['rol'])
        # crear perfil vacío (opcional)
        PerfilUsuario.objects.get_or_create(usuario=user)
        return user

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

class UserWithProfileUpdateSerializer(serializers.Serializer):
    # Campos de User
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    # Campos de PerfilUsuario
    nombres = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    apellidos = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    telefono = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    dni = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    fecha_nacimiento = serializers.DateField(required=False, allow_null=True)
    experiencia_agricola = serializers.IntegerField(required=False, allow_null=True)
    # foto_perfil opcional si luego se habilita

    def validate(self, attrs):
        user = self.context['request'].user
        # username único
        if 'username' in attrs:
            new_username = attrs['username'].strip()
            if not new_username:
                raise serializers.ValidationError({'username': 'No puede estar vacío.'})
            if UserModel.objects.filter(username__iexact=new_username).exclude(id=user.id).exists():
                raise serializers.ValidationError({'username': 'Ya está en uso por otro usuario.'})
        # email único
        if 'email' in attrs:
            new_email = attrs['email'].strip().lower()
            if not new_email:
                raise serializers.ValidationError({'email': 'No puede estar vacío.'})
            if UserModel.objects.filter(email__iexact=new_email).exclude(id=user.id).exists():
                raise serializers.ValidationError({'email': 'Ya está en uso por otro usuario.'})
        # DNI único opcional (corrige indentación)
        # DNI opcional: si quieres unicidad de DNI, descomenta estas líneas:
        # if 'dni' in attrs and attrs['dni']:
        #     if PerfilUsuario.objects.filter(dni=attrs['dni']).exclude(usuario_id=user.id).exists():
        #         raise serializers.ValidationError({'dni': 'DNI ya registrado en otro usuario.'})
        return attrs

    def update(self, instance, validated_data):
        """
        instance = request.user
        Actualiza primero User, luego PerfilUsuario.
        """
        user = instance
        perfil = getattr(user, 'perfilusuario', None)
        from .models import PerfilUsuario

        # User fields
        if 'username' in validated_data:
            user.username = validated_data['username'].strip()
        if 'email' in validated_data:
            user.email = validated_data['email'].strip().lower()
        user.save(update_fields=['username', 'email'])

        # Perfil: crear si no existe
        if perfil is None:
            perfil = PerfilUsuario.objects.create(usuario=user)

        perfil_fields = ['nombres', 'apellidos', 'telefono', 'dni', 'fecha_nacimiento', 'experiencia_agricola']
        for f in perfil_fields:
            if f in validated_data:
                setattr(perfil, f, validated_data[f])
        perfil.save()

        return user

class UserWithProfileSerializer(serializers.Serializer):
    # Lectura combinada
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    rol = serializers.CharField(source='rol.nombre')
    perfil = PerfilUsuarioSerializer(source='perfilusuario', required=False)

class UserDetailSerializer(serializers.ModelSerializer):
    rol = serializers.CharField(source='rol.nombre', read_only=True)
    profile = PerfilUsuarioSerializer(source='perfilusuario', read_only=True)
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'is_active', 'rol', 'date_joined', 'profile'
        ]

# Alias para evitar NameError en views
class AdminUserDetailSerializer(UserDetailSerializer):
    pass

class ProspectoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prospecto
        fields = '__all__'

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({'current_password': 'Contraseña actual incorrecta.'})
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError({'confirm_new_password': 'No coincide con la nueva contraseña.'})
        validate_password(attrs['new_password'], user)
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs['email'].strip().lower()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # No revelar si existe; procesar igual
            attrs['user'] = None
            return attrs
        attrs['user'] = user
        return attrs

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError({'confirm_new_password': 'No coincide.'})
        # Validadores de Django
        validate_password(attrs['new_password'])
        return attrs