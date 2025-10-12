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
    PerfilUsuarioSerializer, UserWithProfileSerializer, UserDetailSerializer
)
from .permissions import HasOperationPermission
from rest_framework.views import APIView

@extend_schema(
    tags=['User'],
    summary='Obtener perfil de usuario por ID',
    description='Devuelve los datos del perfil de un usuario específico según su ID. Solo accesible para administradores.',
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
    description='Actualiza los datos del perfil de un usuario específico según su ID. Solo accesible para administradores.',
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
    description='Devuelve la lista de roles disponibles en el sistema.',
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
        "## OJO: Cuando se crea el usuario el perfil también se crea automáticamente pero esta vacio por lo que no es necesario usar el post sino el PATCH o el PUT.\n\n"
        "Permite consultar, crear o actualizar el perfil del usuario autenticado.\n\n"
        "- **GET**: Devuelve los datos del perfil del usuario autenticado.\n"
        "- **POST**: Crea el perfil del usuario autenticado (si no existe).\n"
        "- **PATCH**: Actualiza parcialmente los datos del perfil del usuario autenticado.\n"
        "- **PUT**: Actualiza completamente todos los datos del perfil del usuario autenticado."
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

@extend_schema(tags=['RBAC'], summary='Listar roles')
class RolViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Rol.objects.all().order_by('id')
    serializer_class = RolSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('administracion', 'ver')]

@extend_schema(tags=['RBAC'], summary='Listar módulos')
class ModuloViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Modulo.objects.all().order_by('id')
    serializer_class = ModuloSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('administracion', 'ver')]

@extend_schema_view(
    list=extend_schema(tags=['RBAC'], summary='Listar permisos por rol/módulo'),
    create=extend_schema(tags=['RBAC'], summary='Conceder permiso a un rol'),
    destroy=extend_schema(tags=['RBAC'], summary='Revocar permiso (por id)'),
    retrieve=extend_schema(tags=['RBAC'], summary='Detalle de permiso por id'),  # <-- Agregado
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

@extend_schema(tags=['RBAC'], summary='Cambiar rol de un usuario', request=UserRoleUpdateSerializer)
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
    list=extend_schema(tags=['RBAC'], summary='Listar overrides'),
    create=extend_schema(tags=['RBAC'], summary='Crear override'),
    retrieve=extend_schema(tags=['RBAC'], summary='Detalle override'),
    update=extend_schema(tags=['RBAC'], summary='Actualizar override'),
    partial_update=extend_schema(tags=['RBAC'], summary='Actualizar parcialmente override'),
    destroy=extend_schema(tags=['RBAC'], summary='Eliminar override'),
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
    get=extend_schema(tags=['Admin'], summary='Listar usuarios', parameters=[
        OpenApiParameter(name='rol', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
        OpenApiParameter(name='is_active', type=OpenApiTypes.BOOL, location=OpenApiParameter.QUERY),
        OpenApiParameter(name='search', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        OpenApiParameter(name='ordering', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
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
    get=extend_schema(tags=['Admin'], summary='Detalle de usuario', responses=AdminUserListSerializer),
    patch=extend_schema(tags=['Admin'], summary='Actualizar usuario (email, activo, rol)', request=AdminUserUpdateSerializer, responses=AdminUserListSerializer),
    put=extend_schema(tags=['Admin'], summary='Actualizar usuario (email, activo, rol)', request=AdminUserUpdateSerializer, responses=AdminUserListSerializer),
)
class AdminUserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    def get_permissions(self):
        return [
            permissions.IsAuthenticated(),
            HasOperationPermission('administracion', 'ver')
        ]