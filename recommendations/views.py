from datetime import datetime
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, OpenApiTypes
from users.permissions import HasOperationPermission, role_name
from .permissions import tiene_permiso, OwnsObjectOrAdmin
from .models import Recommendation
from .serializers import RecommendationSerializer
from parcels.models import Parcela

@extend_schema(
    tags=['Recomendaciones'],
    summary='Listar recomendaciones (global)',
    description=(
        "Lista todas las recomendaciones.\n\n"
        "- Admin/Superadmin/Técnico: ven todas.\n"
        "- Agricultor: solo recomendaciones de sus parcelas.\n"
        "Requiere permiso 'recomendaciones.ver'."
    ),
    parameters=[
        OpenApiParameter(name='tipo', description='Filtrar por tipo', required=False, type=OpenApiTypes.STR),
    ],
    responses={200: RecommendationSerializer(many=True)}
)
class RecommendationListView(generics.ListAPIView):
    serializer_class = RecommendationSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('recomendaciones', 'ver')]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'recomendaciones', 'ver'):
            raise PermissionDenied("No tienes permiso para ver recomendaciones.")
        qs = Recommendation.objects.select_related('parcela').all().order_by('-created_at')
        tipo = self.request.query_params.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)
        if role_name(user) in ['superadmin', 'administrador', 'tecnico']:
            return qs
        # agricultor -> sólo sus parcelas
        return qs.filter(parcela__usuario=user)

@extend_schema(
    tags=['Recomendaciones'],
    summary='Listar / crear recomendaciones para una parcela',
    description=(
        "Listar o crear recomendaciones para la parcela indicada.\n\n"
        "- GET: listado histórico para la parcela.\n"
        "- POST: crear recomendación (propietario o admin/tecnico).\n\n"
        "Body (ejemplo): { 'titulo': '..', 'detalle': '..', 'score': 0.9, 'source': 'rule', 'tipo': 'riego' }"
    ),
    parameters=[
        OpenApiParameter(name='parcela_id', description='ID de la parcela', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH)
    ],
    request=RecommendationSerializer,
    responses={200: RecommendationSerializer(many=True), 201: RecommendationSerializer}
)
class RecommendationByParcelaListCreateView(generics.ListCreateAPIView):
    serializer_class = RecommendationSerializer

    def get_permissions(self):
        # GET -> ver, POST -> crear
        op = 'ver' if self.request.method == 'GET' else 'crear'
        return [permissions.IsAuthenticated(), HasOperationPermission('recomendaciones', op)]

    def get_parcela_or_404(self, parcela_id):
        try:
            return Parcela.objects.get(pk=parcela_id)
        except Parcela.DoesNotExist:
            raise NotFound("Parcela no existe.")

    def get_queryset(self):
        user = self.request.user
        parcela_id = self.kwargs.get('parcela_id')
        parcela = self.get_parcela_or_404(parcela_id)
        if not tiene_permiso(user, 'recomendaciones', 'ver'):
            raise PermissionDenied("No tienes permiso para ver recomendaciones.")
        if role_name(user) in ['superadmin', 'administrador', 'tecnico'] or parcela.usuario == user:
            return Recommendation.objects.filter(parcela=parcela).order_by('-created_at')
        raise PermissionDenied("No tienes permiso para ver las recomendaciones de esta parcela.")

    def perform_create(self, serializer):
        user = self.request.user
        parcela_id = self.kwargs.get('parcela_id')
        parcela = self.get_parcela_or_404(parcela_id)
        if not tiene_permiso(user, 'recomendaciones', 'crear'):
            raise PermissionDenied("No tienes permiso para crear recomendaciones.")
        if role_name(user) not in ['superadmin', 'administrador', 'tecnico'] and parcela.usuario != user:
            raise PermissionDenied("No puedes crear recomendaciones para una parcela que no es tuya.")
        serializer.save(parcela=parcela)

@extend_schema(
    tags=['Recomendaciones'],
    summary='Detalle / actualizar / eliminar recomendación',
    description=(
        "Recupera, actualiza o elimina una recomendación.\n\n"
        "- Acceso: admin/tecnico/superadmin o propietario de la parcela.\n"
        "- Requiere permisos por operación: ver/actualizar/eliminar en 'recomendaciones'."
    ),
    request=RecommendationSerializer,
    responses={200: RecommendationSerializer, 204: None},
    parameters=[
        OpenApiParameter(name='pk', description='ID de la recomendación', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH)
    ]
)
class RecommendationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RecommendationSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), HasOperationPermission('recomendaciones', 'ver'), OwnsObjectOrAdmin()]
        if self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), HasOperationPermission('recomendaciones', 'actualizar'), OwnsObjectOrAdmin()]
        if self.request.method == 'DELETE':
            return [permissions.IsAuthenticated(), HasOperationPermission('recomendaciones', 'eliminar'), OwnsObjectOrAdmin()]
        return [permissions.IsAuthenticated()]

    def get_object(self):
        user = self.request.user
        pk = self.kwargs.get('pk')
        try:
            obj = Recommendation.objects.select_related('parcela').get(pk=pk)
        except Recommendation.DoesNotExist:
            raise NotFound("Recomendación no encontrada.")
        if not tiene_permiso(user, 'recomendaciones', 'ver'):
            raise PermissionDenied("No tienes permiso para ver recomendaciones.")
        if role_name(user) in ['superadmin', 'administrador', 'tecnico']:
            return obj
        if getattr(obj.parcela, 'usuario', None) == user:
            return obj
        raise PermissionDenied("No tienes permiso sobre esta recomendación.")