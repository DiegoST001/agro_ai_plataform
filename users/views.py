from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import PerfilUsuario, Rol
from django.views import View
from rest_framework import viewsets, permissions, status, views, generics
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes, OpenApiExample
from .models import Rol, Modulo, RolesOperaciones, UserOperacionOverride
from authentication.models import User
from .serializers import (
    RolSerializer, ModuloSerializer, RolesOperacionesSerializer, UserRoleUpdateSerializer,
    UserOperacionOverrideSerializer, AdminUserListSerializer, AdminUserUpdateSerializer,
    PerfilUsuarioSerializer, UserWithProfileSerializer, UserDetailSerializer, ProspectoSerializer
)
from .permissions import HasOperationPermission
from rest_framework.views import APIView
from .models import Prospecto
from django.db import transaction

@extend_schema(
    tags=['User'],
    summary='Obtener perfil de usuario por ID',
    description=(
        "Devuelve los datos del perfil de un usuario específico según su ID.\n\n"
        "**Permisos:** Solo administradores pueden acceder.\n\n"
        "**Campos devueltos:** nombres, apellidos, teléfono, DNI, fecha de nacimiento, experiencia agrícola y foto de perfil."
    ),
    responses={
        200: OpenApiExample(
            'Perfil de usuario',
            value={
                "nombres": "Juan",
                "apellidos": "Perez",
                "telefono": "999888777",
                "dni": "12345678",
                "fecha_nacimiento": "1990-01-01",
                "experiencia_agricola": "5 años",
                "foto_perfil": "https://url.com/foto.jpg"
            }
        ),
        404: OpenApiExample('No encontrado', value={"detail": "No encontrado"})
    }
)
class UserProfileView(View):
    def get(self, request, user_id):
        perfil = get_object_or_404(PerfilUsuario, usuario_id=user_id)
        return JsonResponse({
            'nombres': perfil.nombres,
            'apellidos': perfil.apellidos,
            'telefono': perfil.telefono,
            'dni': perfil.dni,
            'fecha_nacimiento': perfil.fecha_nacimiento,
            'experiencia_agricola': perfil.experiencia_agricola,
            'foto_perfil': perfil.foto_perfil,
        })

@extend_schema(
    tags=['User'],
    summary='Actualizar perfil de usuario por ID',
    description=(
        "Actualiza los datos del perfil de un usuario específico según su ID.\n\n"
        "**Permisos:** Solo administradores pueden actualizar perfiles de otros usuarios.\n\n"
        "Envía los campos a modificar en el cuerpo de la solicitud."
    ),
    request=PerfilUsuarioSerializer,
    responses={
        200: OpenApiExample('Perfil actualizado', value={"message": "Perfil actualizado exitosamente."}),
        404: OpenApiExample('No encontrado', value={"detail": "No encontrado"})
    }
)
class UpdateUserProfileView(View):
    def post(self, request, user_id):
        perfil = get_object_or_404(PerfilUsuario, usuario_id=user_id)
        perfil.nombres = request.POST.get('nombres', perfil.nombres)
        perfil.apellidos = request.POST.get('apellidos', perfil.apellidos)
        perfil.telefono = request.POST.get('telefono', perfil.telefono)
        perfil.dni = request.POST.get('dni', perfil.dni)
        perfil.fecha_nacimiento = request.POST.get('fecha_nacimiento', perfil.fecha_nacimiento)
        perfil.experiencia_agricola = request.POST.get('experiencia_agricola', perfil.experiencia_agricola)
        perfil.foto_perfil = request.POST.get('foto_perfil', perfil.foto_perfil)
        perfil.save()
        return JsonResponse({'message': 'Perfil actualizado exitosamente.'})

@extend_schema(
    tags=['User'],
    summary='Listar roles de usuario',
    description=(
        "Devuelve la lista de roles disponibles en el sistema.\n\n"
        "Cada rol incluye su nombre y descripción.\n\n"
        "Útil para asignar roles a usuarios ou mostrar opciones en formularios."
    ),
    responses={
        200: OpenApiExample(
            'Lista de roles',
            value=[
                {"id": 1, "nombre": "Administrador", "descripcion": "Acceso total"},
                {"id": 2, "nombre": "Cliente", "descripcion": "Acceso limitado"}
            ]
        )
    }
)
class UserRolesView(View):
    def get(self, request):
        roles = Rol.objects.all().values('id', 'nombre', 'descripcion')
        return JsonResponse(list(roles), safe=False)

@extend_schema(
    tags=['User'],
    summary='Ver, crear o actualizar perfil del usuario autenticado',
    description=(
        "Permite consultar, crear o actualizar el perfil del usuario autenticado.\n\n"
        "- **GET:** Devuelve el perfil del usuario autenticado.\n"
        "- **POST:** Crea el perfil si no existe (normalmente no se usa, el perfil se crea automáticamente).\n"
        "- **PATCH:** Actualiza parcialmente el perfil.\n"
        "- **PUT:** Actualiza completamente el perfil.\n\n"
        "**Nota:** El perfil se crea vacío al crear el usuario, por lo que normalmente solo se usa PATCH o PUT para actualizar."
    ),
    request=PerfilUsuarioSerializer,
    responses=PerfilUsuarioSerializer,
    examples=[
        OpenApiExample(
            'Ejemplo de perfil',
            value={
                "nombres": "Juan",
                "apellidos": "Perez",
                "telefono": "999888777",
                "dni": "12345678",
                "fecha_nacimiento": "1990-01-01",
                "experiencia_agricola": 5,
                # "foto_perfil": "https://url.com/foto.jpg"
            }
        )
    ]
)
class PerfilUsuarioView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Devuelve los datos del usuario autenticado con el perfil anidado.
        """
        serializer = UserWithProfileSerializer(request.user)
        return Response(serializer.data)

    def post(self, request):
        """
        Crea el perfil del usuario autenticado si no existe.
        """
        if PerfilUsuario.objects.filter(usuario=request.user).exists():
            return Response({'detail': 'Perfil ya existe.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = PerfilUsuarioSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(usuario=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        """
        Actualiza parcialmente los datos del perfil del usuario autenticado.
        """
        perfil = PerfilUsuario.objects.get(usuario=request.user)
        serializer = PerfilUsuarioSerializer(perfil, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """
        Actualiza completamente los datos del perfil del usuario autenticado.
        """
        perfil = PerfilUsuario.objects.get(usuario=request.user)
        serializer = PerfilUsuarioSerializer(perfil, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(tags=['RBAC'], summary='Listar roles', description="Devuelve todos los roles del sistema. Solo administradores pueden acceder.")
class RolViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Rol.objects.all().order_by('id')
    serializer_class = RolSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('administracion', 'ver')]

@extend_schema(tags=['RBAC'], summary='Listar módulos', description="Devuelve todos los módulos del sistema. Solo administradores pueden acceder.")
class ModuloViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Modulo.objects.all().order_by('id')
    serializer_class = ModuloSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('administracion', 'ver')]

@extend_schema_view(
    list=extend_schema(
        tags=['RBAC'],
        summary='Listar permisos por rol/módulo',
        description="Devuelve los permisos asignados a cada rol y módulo. Solo administradores pueden consultar."
    ),
    create=extend_schema(
        tags=['RBAC'],
        summary='Conceder permiso a un rol',
        description="Permite asignar un permiso específico a un rol en un módulo. Solo administradores pueden modificar."
    ),
    destroy=extend_schema(
        tags=['RBAC'],
        summary='Revocar permiso (por id)',
        description="Elimina un permiso asignado a un rol. Solo administradores pueden modificar."
    ),
    retrieve=extend_schema(
        tags=['RBAC'],
        summary='Detalle de permiso por id',
        description="Devuelve el detalle de un permiso específico por id. Solo administradores pueden consultar."
    ),
)
class RolesOperacionesViewSet(viewsets.ModelViewSet):
    queryset = RolesOperaciones.objects.select_related('rol', 'modulo', 'operacion').all()
    serializer_class = RolesOperacionesSerializer
    http_method_names = ['get', 'post', 'delete']
    filterset_fields = ['rol', 'modulo']  # ?rol=1&modulo=2

    def get_permissions(self):
        base = [permissions.IsAuthenticated()]
        if self.action in ['list', 'retrieve']:
            base.append(HasOperationPermission('administracion', 'ver'))
        else:
            base.append(HasOperationPermission('administracion', 'actualizar'))
        return base

@extend_schema(
    tags=['RBAC'],
    summary='Cambiar rol de un usuario',
    description=(
        "Permite cambiar el rol de un usuario existente.\n\n"
        "**Permisos:** Solo administradores pueden cambiar roles.\n"
        "Envía el nuevo rol en el cuerpo de la solicitud."
    ),
    request=UserRoleUpdateSerializer
)
class UserRoleUpdateView(views.APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('usuarios', 'actualizar')]

    def patch(self, request, user_id: int):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        s = UserRoleUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.update(user, s.validated_data)
        return Response({'detail': 'Rol actualizado', 'user_id': user.id, 'rol_id': user.rol_id})

@extend_schema_view(
    list=extend_schema(
        tags=['RBAC'],
        summary='Listar overrides',
        description="Devuelve la lista de overrides de permisos por usuario. Solo administradores pueden consultar."
    ),
    create=extend_schema(
        tags=['RBAC'],
        summary='Crear override',
        description="Permite crear un override de permisos para un usuario. Solo administradores pueden modificar."
    ),
    retrieve=extend_schema(
        tags=['RBAC'],
        summary='Detalle override',
        description="Devuelve el detalle de un override de permisos por usuario. Solo administradores pueden consultar."
    ),
    update=extend_schema(
        tags=['RBAC'],
        summary='Actualizar override',
        description="Actualiza un override de permisos para un usuario. Solo administradores pueden modificar."
    ),
    partial_update=extend_schema(
        tags=['RBAC'],
        summary='Actualizar parcialmente override',
        description="Actualiza parcialmente un override de permisos para un usuario. Solo administradores pueden modificar."
    ),
    destroy=extend_schema(
        tags=['RBAC'],
        summary='Eliminar override',
        description="Elimina un override de permisos para un usuario. Solo administradores pueden modificar."
    ),
)
class UserOperacionOverrideViewSet(viewsets.ModelViewSet):
    queryset = UserOperacionOverride.objects.select_related('user', 'modulo', 'operacion').all()
    serializer_class = UserOperacionOverrideSerializer
    filterset_fields = ['user', 'modulo', 'operacion', 'allow']

    def get_permissions(self):
        base = [permissions.IsAuthenticated()]
        if self.action in ['list', 'retrieve']:
            base.append(HasOperationPermission('administracion', 'ver'))
        else:
            base.append(HasOperationPermission('administracion', 'actualizar'))
        return base

@extend_schema_view(
    get=extend_schema(
        tags=['Admin'],
        summary='Listar usuarios',
        description=(
            "Devuelve la lista de usuarios registrados en el sistema.\n\n"
            "Permite filtrar por rol, estado activo, búsqueda y ordenamiento.\n"
            "**Permisos:** Solo administradores pueden acceder."
        ),
        parameters=[
            OpenApiParameter(name='rol', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, description="Filtrar por rol"),
            OpenApiParameter(name='is_active', type=OpenApiTypes.BOOL, location=OpenApiParameter.QUERY, description="Filtrar por estado activo"),
            OpenApiParameter(name='search', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="Buscar por username o email"),
            OpenApiParameter(name='ordering', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="Ordenar por campo"),
        ],
        responses=AdminUserListSerializer(many=True),
    )
)
class AdminUserListView(generics.ListAPIView):
    queryset = User.objects.select_related('rol').all()
    serializer_class = AdminUserListSerializer
    filterset_fields = ['rol', 'is_active']
    search_fields = ['username', 'email']
    ordering_fields = ['date_joined', 'username', 'email']
    ordering = ['-date_joined']

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('administracion', 'ver')]

@extend_schema_view(
    get=extend_schema(
        tags=['Admin'],
        summary='Detalle de usuario',
        description="Devuelve el detalle de un usuario específico. Solo administradores pueden consultar.",
        responses=AdminUserListSerializer,
    ),
    patch=extend_schema(
        tags=['Admin'],
        summary='Actualizar usuario (email, activo, rol)',
        description="Actualiza los datos básicos de un usuario (email, estado activo, rol). Solo administradores pueden modificar.",
        request=AdminUserUpdateSerializer,
        responses=AdminUserListSerializer,
    ),
    put=extend_schema(
        tags=['Admin'],
        summary='Actualizar usuario (email, activo, rol)',
        description="Actualiza completamente los datos básicos de un usuario. Solo administradores pueden modificar.",
        request=AdminUserUpdateSerializer,
        responses=AdminUserListSerializer,
    ),
)
class AdminUserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    def get_permissions(self):
        return [
            permissions.IsAuthenticated(),
            HasOperationPermission('administracion', 'ver')
        ]

@extend_schema(
    tags=['Prospectos'],
    summary='Listar prospectos',
    description=(
        "Devuelve la lista de prospectos registrados en el sistema.\n\n"
        "**Permisos:** Solo administradores pueden acceder."
    ),
    responses=ProspectoSerializer(many=True)
)
class ProspectoListView(generics.ListAPIView):
    queryset = Prospecto.objects.all()
    serializer_class = ProspectoSerializer
    permission_classes = [permissions.IsAdminUser]  # Solo admin

@extend_schema(
    tags=['Prospectos'],
    summary='Detalle de prospecto',
    description=(
        "Devuelve los datos de un prospecto específico por ID.\n\n"
        "**Permisos:** Solo administradores pueden acceder."
    ),
    responses=ProspectoSerializer
)
class ProspectoDetailView(generics.RetrieveAPIView):
    queryset = Prospecto.objects.all()
    serializer_class = ProspectoSerializer
    permission_classes = [permissions.IsAdminUser]  # Solo admin

@extend_schema(
    tags=['Prospectos'],
    summary='Aceptar prospecto y crear agricultor',
    description=(
        "Acepta un prospecto y crea un usuario agricultor con los datos del prospecto.\n\n"
        "Permite modificar el correo y asignar un username y contraseña.\n\n"
        "Notas:\n"
        "- `username` y `password` son obligatorios.\n"
        "- `email` es opcional: si no se envía se usará el correo registrado en el prospecto (`prospecto.correo`).\n\n"
        "**Permisos:** Solo administradores pueden acceder."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "example": "nuevo_usuario"},
                "password": {"type": "string", "example": "contraseña_segura"},
                "email": {"type": "string", "format": "email", "example": "nuevo@email.com"},
            },
            "required": ["username", "password"],  # email queda opcional
        }
    },
    responses={
        201: OpenApiExample('Agricultor creado', value={"msg": "Agricultor creado", "user_id": 123}),
        400: OpenApiExample('Error', value={"error": "Username ya existe / Correo ya existe / username/password son requeridos"}),
        404: OpenApiExample('No encontrado', value={"detail": "Prospecto no encontrado."}),
        500: OpenApiExample('Error servidor', value={"error": "Rol agricultor no configurado."})
    },
    examples=[
        OpenApiExample('Aceptar con email (override)', value={"username":"agro01","password":"Secreto123","email":"nuevo@demo.com"}),
        OpenApiExample('Aceptar sin email (usar correo del prospecto)', value={"username":"agro02","password":"Secreto123"})
    ]
)
class ProspectoAceptarView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        try:
            prospecto = Prospecto.objects.get(pk=pk)
        except Prospecto.DoesNotExist:
            return Response({'detail': 'Prospecto no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        username = (request.data.get('username') or '').strip()
        password = request.data.get('password')
        # email opcional: si no se provee se usa el correo del prospecto
        email = request.data.get('email') or prospecto.correo

        # Validaciones básicas
        if not username:
            return Response({'error': 'username es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({'error': 'password es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        if not email:
            return Response({'error': 'email no disponible en prospecto y no fue proporcionado.'}, status=status.HTTP_400_BAD_REQUEST)

        # Unicidad (case-insensitive)
        if User.objects.filter(username__iexact=username).exists():
            return Response({'error': 'Username ya existe'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email__iexact=email).exists():
            return Response({'error': 'Correo ya existe'}, status=status.HTTP_400_BAD_REQUEST)

        # Crear usuario y perfil dentro de una transacción
        try:
            rol_agricultor = Rol.objects.get(nombre__iexact='agricultor')
        except Rol.DoesNotExist:
            return Response({'error': 'Rol agricultor no configurado.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        with transaction.atomic():
            user = User.objects.create_user(username=username, email=email, password=password, is_active=True)
            user.rol = rol_agricultor
            user.save()

            PerfilUsuario.objects.create(
                usuario=user,
                nombres=prospecto.nombre_completo,
                telefono=prospecto.telefono,
                dni=prospecto.dni,
            )

            prospecto.estado = 'aprobado'
            prospecto.save()

        return Response({'msg': 'Agricultor creado', 'user_id': user.id}, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Public'],
    summary='Total de usuarios registrados',
    description=(
        "Devuelve el total de usuarios registrados en el sistema.\n\n"
        "Endpoint público, útil para mostrar en la página de bienvenida."
    ),
    responses={
        200: {
            "type": "object",
            "properties": {
                "total": {"type": "integer", "example": 120}
            }
        }
    }
)
class UsuariosTotalPublicView(APIView):
    permission_classes = []  # Público, sin autenticación

    def get(self, request):
        from authentication.models import User
        total = User.objects.count()
        return Response({"total": total})

@extend_schema(
    tags=['Public'],
    summary='Registrar prospecto',
    description=(
        "Permite a cualquier usuario registrar sus datos como prospecto para ser contactado y eventualmente convertirse en agricultor.\n\n"
        "No requiere autenticación. El prospecto queda en estado 'pendiente' hasta que un administrador lo apruebe."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "nombre_completo": {"type": "string", "example": "Juan Pérez"},
                "dni": {"type": "string", "example": "12345678"},
                "correo": {"type": "string", "example": "juan@email.com"},
                "telefono": {"type": "string", "example": "999888777"},
                "ubicacion_parcela": {"type": "string", "example": "Cusco, sector 5"},
                "descripcion_terreno": {"type": "string", "example": "Terreno arcilloso, 2 hectáreas"},
            },
            "required": ["nombre_completo", "dni", "correo", "telefono", "ubicacion_parcela", "descripcion_terreno"]
        }
    },
    responses={
        201: OpenApiExample('Prospecto registrado', value={"msg": "Prospecto registrado"}),
        400: OpenApiExample('Error', value={"error": "Correo ya registrado"})
    }
)
class ProspectoPublicCreateView(APIView):
    permission_classes = []  # Público

    def post(self, request):
        data = request.data
        from .models import Prospecto
        if Prospecto.objects.filter(correo=data.get('correo')).exists():
            return Response({'error': 'Correo ya registrado'}, status=status.HTTP_400_BAD_REQUEST)
        prospecto = Prospecto.objects.create(
            nombre_completo=data.get('nombre_completo'),
            dni=data.get('dni'),
            correo=data.get('correo'),
            telefono=data.get('telefono'),
            ubicacion_parcela=data.get('ubicacion_parcela'),
            descripcion_terreno=data.get('descripcion_terreno'),
            estado='pendiente'
        )
        return Response({'msg': 'Prospecto registrado'}, status=status.HTTP_201_CREATED)