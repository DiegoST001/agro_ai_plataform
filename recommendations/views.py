from datetime import datetime
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, NotFound
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from users.permissions import HasOperationPermission, role_name
from .permissions import tiene_permiso, OwnsObjectOrAdmin
from .models import Recommendation
from .serializers import RecommendationSerializer
from parcels.models import Parcela

@extend_schema(
    tags=['Alertas'],
    summary='Listar alertas por parcela',
    description=(
        "Lista las alertas asociadas a la parcela indicada.\n\n"
        "- Solo GET está permitido en este endpoint (no crear desde API pública).\n"
        "- Admin/Superadmin/Técnico: ven todas.\n"
        "- Agricultor: solo alertas de sus parcelas.\n"
        "Requiere permiso 'alertas.ver'."
    ),
    parameters=[
        OpenApiParameter(name='tipo', description='Filtrar por tipo', required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name='parcela_id', description='ID de la parcela (path)', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH),
    ],
    responses={200: RecommendationSerializer(many=True)}
)
class RecommendationByParcelaListView(generics.ListAPIView):
    """
    Endpoint sólo para listar alertas/recomendaciones asociadas a una parcela.
    No permite creación vía API pública.
    """
    serializer_class = RecommendationSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('alertas', 'ver')]

    def get_parcela_or_404(self, parcela_id):
        try:
            return Parcela.objects.get(pk=parcela_id)
        except Parcela.DoesNotExist:
            raise NotFound("Parcela no existe.")

    def get_queryset(self):
        user = self.request.user
        parcela_id = self.kwargs.get('parcela_id')
        parcela = self.get_parcela_or_404(parcela_id)
        if not tiene_permiso(user, 'alertas', 'ver'):
            raise PermissionDenied("No tienes permiso para ver alertas.")
        if getattr(parcela, 'usuario', None) != user:
            # Siempre restringido al dueño, sin excepciones por rol
            raise PermissionDenied("No tienes acceso a esta parcela.")
        qs = Recommendation.objects.select_related('parcela').filter(parcela=parcela).order_by('-created_at')
        tipo = self.request.query_params.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)
        return qs

@extend_schema(
    tags=['Alertas'],
    summary='Listar alertas del usuario (todas sus parcelas)',
    description=(
        "Devuelve todas las alertas/recomendaciones asociadas a las parcelas del usuario autenticado.\n"
        "Roles admin/superadmin/técnico: ven todas las alertas del sistema.\n"
        "Agricultor: solo alertas de sus propias parcelas.\n"
        "Filtros: ?tipo=alerta&severity=high&status=new"
    ),
    parameters=[
        OpenApiParameter(name='tipo', required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name='severity', required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name='status', required=False, type=OpenApiTypes.STR),
    ],
    responses={200: RecommendationSerializer(many=True)}
)
class RecommendationUserListView(generics.ListAPIView):
    serializer_class = RecommendationSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('alertas', 'ver')]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'alertas', 'ver'):
            raise PermissionDenied("No tienes permiso para ver alertas.")
        qs = Recommendation.objects.select_related('parcela').filter(parcela__usuario=user).order_by('-created_at')
        tipo = self.request.query_params.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)
        severity = self.request.query_params.get('severity')
        if severity:
            qs = qs.filter(severity=severity)
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs