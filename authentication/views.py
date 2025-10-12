from rest_framework import status, views, permissions
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from drf_spectacular.utils import extend_schema, OpenApiExample, extend_schema_view
from .serializers import UserRegisterSerializer, AccountSerializer, PerfilUpdateSerializer
from .models import User
from users.models import PerfilUsuario

@extend_schema(
    tags=['Auth'],
    summary='Registrar nuevo usuario',
    description='Permite registrar un nuevo usuario en la plataforma. Retorna el token de autenticación y los datos básicos del usuario.',
    request=UserRegisterSerializer,
    responses={
        201: OpenApiExample(
            'Respuesta exitosa',
            value={"token": "abc123", "user": {"user_id": 1, "username": "agri01", "email": "a@b.com"}}
        ),
        400: OpenApiExample('Error', value={"detail": "Datos inválidos"})
    },
    examples=[
        OpenApiExample('Registro', value={"username":"agri01","email":"a@b.com","password":"***"})
    ]
)
class RegisterView(views.APIView):
    permission_classes = []

    def post(self, request):
        s = UserRegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = s.save()
        user = User.objects.get(id=result['user_id'])
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user': result}, status=status.HTTP_201_CREATED)

@extend_schema(
    tags=['Auth'],
    summary='Login de usuario',
    description='Permite iniciar sesión con usuario y contraseña. Retorna el token de autenticación y los datos básicos del usuario.',
    request=AccountSerializer,
    responses={
        200: OpenApiExample(
            'Respuesta exitosa',
            value={"token": "abc123", "user": {"user_id": 1, "username": "agri01", "email": "a@b.com"}}
        ),
        400: OpenApiExample('Error', value={"detail": "Credenciales inválidas"})
    },
    examples=[
        OpenApiExample('Login', value={"username":"agri01","password":"***"})
    ]
)
class LoginView(views.APIView):
    permission_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if not user or not user.is_active:
            return Response({'detail': 'Credenciales inválidas'}, status=status.HTTP_400_BAD_REQUEST)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user': {'user_id': user.id, 'username': user.username, 'email': user.email}}, status=status.HTTP_200_OK)

@extend_schema(
    tags=['Auth'],
    summary='Cerrar sesión (invalidar token)',
    description='Cierra la sesión del usuario actual e invalida el token de autenticación.',
    responses={204: OpenApiExample('Logout exitoso', value={})}
)
class LogoutView(views.APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if getattr(request, 'auth', None):
            request.auth.delete()
        else:
            Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@extend_schema_view(
    get=extend_schema(
        tags=['Auth'],
        summary='Datos de mi cuenta',
        description='Devuelve los datos básicos del usuario autenticado.',
        responses=AccountSerializer,
    ),
    patch=extend_schema(
        tags=['Auth'],
        summary='Actualizar mi perfil',
        description='Permite actualizar los datos del perfil del usuario autenticado.',
        request=PerfilUpdateSerializer,
        responses=AccountSerializer,
    )
)
class MeView(views.APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(AccountSerializer(request.user).data, status=status.HTTP_200_OK)

    def patch(self, request):
        perfil, _ = PerfilUsuario.objects.get_or_create(usuario=request.user)
        s = PerfilUpdateSerializer(perfil, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(AccountSerializer(request.user).data, status=status.HTTP_200_OK)