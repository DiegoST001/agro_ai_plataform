from rest_framework import permissions, generics
from .serializers import ParcelaCreateSerializer, ParcelaListSerializer, ParcelaUpdateSerializer, ParcelaBasicListSerializer
from .models import Parcela
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
from users.permissions import HasOperationPermission

@extend_schema_view(
    get=extend_schema(tags=['Parcelas'], summary='Listar parcelas', parameters=[
        OpenApiParameter(name='ubicacion', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        OpenApiParameter(name='search', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        OpenApiParameter(name='ordering', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
    ]),
    post=extend_schema(tags=['Parcelas'], summary='Crear parcela y asignar plan', request=ParcelaCreateSerializer),
)
class ParcelaListCreateView(generics.ListCreateAPIView):
    queryset = Parcela.objects.all()
    filterset_fields = ['ubicacion', 'latitud', 'longitud']
    search_fields = ['nombre', 'ubicacion']
    ordering_fields = ['created_at', 'nombre', 'tamano_hectareas']
    ordering = ['-created_at']

    def get_queryset(self):
        return Parcela.objects.filter(usuario=self.request.user)

    def get_serializer_class(self):
        return ParcelaCreateSerializer if self.request.method == 'POST' else ParcelaListSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    def get_permissions(self):
        base = [permissions.IsAuthenticated()]
        if self.request.method == 'GET':
            base.append(HasOperationPermission('parcelas', 'ver'))
        elif self.request.method == 'POST':
            base.append(HasOperationPermission('parcelas', 'crear'))
        return base

@extend_schema_view(
    get=extend_schema(tags=['Parcelas'], summary='Detalle de parcela'),
    patch=extend_schema(tags=['Parcelas'], summary='Editar parcialmente', request=ParcelaUpdateSerializer),
    put=extend_schema(tags=['Parcelas'], summary='Editar', request=ParcelaUpdateSerializer),
)
class ParcelaDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ParcelaUpdateSerializer

    def get_queryset(self):
        return Parcela.objects.filter(usuario=self.request.user)

    def get_permissions(self):
        base = [permissions.IsAuthenticated()]
        if self.request.method == 'GET':
            base.append(HasOperationPermission('parcelas', 'ver'))
        else:
            base.append(HasOperationPermission('parcelas', 'actualizar'))
        return base

@extend_schema_view(
    get=extend_schema(
        tags=['Admin'],
        summary='Listar todas las parcelas',
        parameters=[
            OpenApiParameter(name='usuario', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter(name='ubicacion', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name='search', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name='ordering', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        ],
        responses=ParcelaListSerializer(many=True),
    )
)
class AdminParcelaListView(generics.ListAPIView):
    serializer_class = ParcelaBasicListSerializer  # Solo datos básicos
    queryset = Parcela.objects.select_related('usuario').all()
    filterset_fields = ['usuario', 'ubicacion']
    search_fields = ['nombre', 'ubicacion', 'usuario__username']
    ordering_fields = ['created_at', 'nombre', 'tamano_hectareas']
    ordering = ['-created_at']

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('administracion', 'ver')]

@extend_schema_view(
    get=extend_schema(tags=['Admin'], summary='Detalle de parcela', responses=ParcelaListSerializer),
    patch=extend_schema(tags=['Admin'], summary='Editar parcela (campos básicos)', request=ParcelaUpdateSerializer, responses=ParcelaListSerializer),
    put=extend_schema(tags=['Admin'], summary='Editar parcela', request=ParcelaUpdateSerializer, responses=ParcelaListSerializer),
)
class AdminParcelaDetailView(generics.RetrieveAPIView):
    serializer_class = ParcelaListSerializer  # Todos los datos completos
    queryset = Parcela.objects.all()

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('administracion', 'ver')]




