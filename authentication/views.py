from rest_framework import status, views, permissions, generics
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from drf_spectacular.utils import extend_schema, OpenApiExample, extend_schema_view
from .serializers import UserRegisterSerializer, AccountSerializer, PerfilUpdateSerializer
from .models import User
from users.models import PerfilUsuario, RolesOperaciones  # modelo que relaciona rol->modulo->operacion



@extend_schema(
    tags=['Auth'],
    summary='Login de usuario',
    description=(
        "Permite iniciar sesión con username O email usando un único campo `login` + `password`.\n\n"
        "Campos aceptados (JSON):\n"
        "- login: username o email (recomendado, facilita frontend)\n"
        "- password: obligatorio\n\n"
        "También soporta los campos legacy `username` o `email`.\n\n"
        "Ejemplos:\n"
        "- {\"login\":\"agri01\",\"password\":\"***\"}\n"
        "- {\"login\":\"a@b.com\",\"password\":\"***\"}\n"
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "login": {"type": "string", "example": "agri01 or a@b.com"},
                "username": {"type": "string", "example": "agri01"},
                "email": {"type": "string", "format": "email", "example": "a@b.com"},
                "password": {"type": "string", "example": "tu_contraseña"}
            },
            "required": ["password"],
            "description": "Enviar `login` (recomendado) o `username`/`email` además de `password`"
        }
    },
    responses={
        200: {
            "type": "object",
            "properties": {
                "token": {"type": "string", "example": "abc123"},
                "user": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "integer", "example": 1},
                        "username": {"type": "string", "example": "agri01"},
                        "email": {"type": "string", "example": "a@b.com"}
                    }
                }
            }
        },
        400: {"type": "object", "properties": {"detail": {"type": "string"}}}
    },
    examples=[
        OpenApiExample('Login username', value={"login":"agri01","password":"contraseña"}),
        OpenApiExample('Login email', value={"login":"a@b.com","password":"contraseña"})
    ]
)
class LoginView(views.APIView):
    permission_classes = []

    def post(self, request):
        data = request.data or request.POST
        login = data.get('login') or data.get('username') or data.get('email')
        password = data.get('password')

        if not password or not login:
            return Response({'detail': 'Se requiere login (username o email) y password.'}, status=status.HTTP_400_BAD_REQUEST)

        username = None

        # Si parece un email (contiene '@'), intentar resolver usuario por email
        if '@' in str(login):
            try:
                user_obj = User.objects.get(email__iexact=login)
                username = user_obj.get_username()
            except User.DoesNotExist:
                return Response({'detail': 'Credenciales inválidas'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            username = login

        user = authenticate(request, username=username, password=password)
        if not user or not user.is_active:
            return Response({'detail': 'Credenciales inválidas'}, status=status.HTTP_400_BAD_REQUEST)

        token, _ = Token.objects.get_or_create(user=user)

        # construir mapa de permisos por módulo para el rol del usuario
        perms_qs = RolesOperaciones.objects.filter(rol=user.rol).select_related('modulo','operacion')
        permissions_map = {}
        for r in perms_qs:
            m = r.modulo.nombre
            permissions_map.setdefault(m, []).append(r.operacion.nombre)

        rol_nombre = getattr(getattr(user, 'rol', None), 'nombre', None)
        return Response({
            'token': token.key,
            'user': {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'rol': rol_nombre,
                'permissions': permissions_map,   # <- map módulo -> [operacion,...]
            }
        }, status=status.HTTP_200_OK)

@extend_schema(
    tags=['Auth'],
    summary='Cerrar sesión (invalidar token)',
    description='Cierra la sesión del usuario actual e invalida el token de autenticación.',
    request=None,
    responses={204: None},
    examples=[OpenApiExample('Logout exitoso', value={})]
)
class LogoutView(generics.GenericAPIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None

    def post(self, request, *args, **kwargs):
        if getattr(request, 'auth', None):
            request.auth.delete()
        else:
            Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)























# @extend_schema(
#     tags=['Auth'],
#     summary='Registrar nuevo usuario',
#     description='Permite registrar un nuevo usuario en la plataforma. Retorna el token de autenticación y los datos básicos del usuario.',
#     request=UserRegisterSerializer,
#     responses={
#         201: OpenApiExample(
#             'Respuesta exitosa',
#             value={"token": "abc123", "user": {"user_id": 1, "username": "agri01", "email": "a@b.com"}}
#         ),
#         400: OpenApiExample('Error', value={"detail": "Datos inválidos"})
#     },
#     examples=[
#         OpenApiExample('Registro', value={"username":"agri01","email":"a@b.com","password":"***"})
#     ]
# )
# class RegisterView(views.APIView):
#     permission_classes = []

#     def post(self, request):
#         s = UserRegisterSerializer(data=request.data)
#         s.is_valid(raise_exception=True)
#         result = s.save()
#         user = User.objects.get(id=result['user_id'])
#         token, _ = Token.objects.get_or_create(user=user)
#         return Response({'token': token.key, 'user': result}, status=status.HTTP_201_CREATED)









# @extend_schema_view(
#     get=extend_schema(
#         tags=['Auth'],
#         summary='Datos de mi cuenta',
#         description='Devuelve los datos básicos del usuario autenticado.',
#         responses=AccountSerializer,
#     ),
#     patch=extend_schema(
#         tags=['Auth'],
#         summary='Actualizar mi perfil',
#         description='Permite actualizar los datos del perfil del usuario autenticado.',
#         request=PerfilUpdateSerializer,
#         responses=AccountSerializer,
#     )
# )
# class MeView(views.APIView):
#     authentication_classes = [TokenAuthentication, SessionAuthentication]
#     permission_classes = [permissions.IsAuthenticated]

#     def get(self, request):
#         return Response(AccountSerializer(request.user).data, status=status.HTTP_200_OK)

#     def patch(self, request):
#         perfil, _ = PerfilUsuario.objects.get_or_create(usuario=request.user)
#         s = PerfilUpdateSerializer(perfil, data=request.data, partial=True)
#         s.is_valid(raise_exception=True)
#         s.save()
#         return Response(AccountSerializer(request.user).data, status=status.HTTP_200_OK)