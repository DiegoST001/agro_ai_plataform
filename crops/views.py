from rest_framework import generics, permissions
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter, OpenApiTypes

# usar el adapter de permisos local (exports iguales a users.permissions)
from .permissions import HasOperationPermission, role_name, tiene_permiso

from .models import Cultivo, Variedad, Etapa, ReglaPorEtapa
from .serializers import (
    CultivoSerializer, CultivoSimpleSerializer,
    VariedadSerializer, VariedadSimpleSerializer,
    EtapaSerializer, EtapaSimpleSerializer,
    ReglaPorEtapaSerializer
)


@extend_schema_view(
    get=extend_schema(tags=['cultivos'], summary='Listar cultivos'),
    post=extend_schema(tags=['cultivos'], summary='Crear cultivo'),
)
class CultivoListCreateView(generics.ListCreateAPIView):
    """
    Listar y crear cultivos.
    GET: requiere 'cultivos.ver'.
    POST: requiere 'cultivos.crear'.
    """
    queryset = Cultivo.objects.all().order_by('nombre')
    serializer_class = CultivoSerializer

    def get_permissions(self):
        op = 'ver' if self.request.method == 'GET' else 'crear'
        return [permissions.IsAuthenticated(), HasOperationPermission('cultivos', op)]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'cultivos', 'ver'):
            return Cultivo.objects.none()
        return self.queryset


@extend_schema_view(
    get=extend_schema(tags=['cultivos'], summary='Detalle de cultivo'),
    put=extend_schema(tags=['cultivos'], summary='Actualizar cultivo'),
    patch=extend_schema(tags=['cultivos'], summary='Actualizar parcialmente cultivo'),
    delete=extend_schema(tags=['cultivos'], summary='Eliminar cultivo'),
)
class CultivoDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Recuperar, actualizar o eliminar un cultivo por id.
    """
    queryset = Cultivo.objects.all()
    serializer_class = CultivoSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), HasOperationPermission('cultivos', 'ver')]
        if self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), HasOperationPermission('cultivos', 'actualizar')]
        if self.request.method == 'DELETE':
            return [permissions.IsAuthenticated(), HasOperationPermission('cultivos', 'eliminar')]
        return [permissions.IsAuthenticated()]


@extend_schema_view(
    get=extend_schema(tags=['variedades'], summary='Listar variedades'),
    post=extend_schema(tags=['variedades'], summary='Crear variedad'),
)
class VariedadListCreateView(generics.ListCreateAPIView):
    """
    Listar variedades (puede filtrarse por cultivo) y crear variedad para un cultivo.
    - Si se crea vía /cultivos/{cultivo_id}/variedades/ el cultivo será asignado automáticamente.
    """
    serializer_class = VariedadSerializer

    def get_permissions(self):
        op = 'ver' if self.request.method == 'GET' else 'crear'
        # cuando se accede anidado por cultivo, verificar permisos de cultivos para crear/listar
        if self.kwargs.get('cultivo_id'):
            return [permissions.IsAuthenticated(), HasOperationPermission('cultivos', op)]
        return [permissions.IsAuthenticated(), HasOperationPermission('variedades', op)]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'variedades', 'ver'):
            return Variedad.objects.none()
        qs = Variedad.objects.select_related('cultivo').all().order_by('cultivo__nombre', 'nombre')
        cultivo_id = self.kwargs.get('cultivo_id') or self.request.query_params.get('cultivo')
        if cultivo_id:
            qs = qs.filter(cultivo_id=cultivo_id)
        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        cultivo_id = self.kwargs.get('cultivo_id') or self.request.query_params.get('cultivo') or self.request.data.get('cultivo')
        if cultivo_id:
            try:
                ctx['cultivo'] = Cultivo.objects.get(pk=cultivo_id)
            except Cultivo.DoesNotExist:
                ctx['cultivo'] = None
        return ctx

    def perform_create(self, serializer):
        cultivo_id = self.kwargs.get('cultivo_id') or self.request.data.get('cultivo')
        if not cultivo_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"cultivo": "Proporciona cultivo en la URL (/cultivos/{id}/variedades/) o en el body."})
        try:
            cultivo = Cultivo.objects.get(pk=cultivo_id)
        except Cultivo.DoesNotExist:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"cultivo": "Cultivo no existe."})
        serializer.save(cultivo=cultivo)


@extend_schema_view(
    get=extend_schema(tags=['variedades'], summary='Detalle de variedad'),
    put=extend_schema(tags=['variedades'], summary='Actualizar variedad'),
    patch=extend_schema(tags=['variedades'], summary='Actualizar parcialmente variedad'),
    delete=extend_schema(tags=['variedades'], summary='Eliminar variedad'),
)
class VariedadDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Recuperar, actualizar o eliminar una variedad.
    """
    queryset = Variedad.objects.select_related('cultivo').all()
    serializer_class = VariedadSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), HasOperationPermission('variedades', 'ver')]
        if self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), HasOperationPermission('variedades', 'actualizar')]
        if self.request.method == 'DELETE':
            return [permissions.IsAuthenticated(), HasOperationPermission('variedades', 'eliminar')]
        return [permissions.IsAuthenticated()]


@extend_schema_view(
    get=extend_schema(tags=['etapas'], summary='Listar etapas'),
    post=extend_schema(tags=['etapas'], summary='Crear etapa'),
)
class EtapaListCreateView(generics.ListCreateAPIView):
    """
    Listar etapas (global o por variedad) y crear etapa para una variedad.
    """
    serializer_class = EtapaSerializer

    def get_permissions(self):
        op = 'ver' if self.request.method == 'GET' else 'crear'
        return [permissions.IsAuthenticated(), HasOperationPermission('etapas', op)]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'etapas', 'ver'):
            return Etapa.objects.none()
        qs = Etapa.objects.select_related('variedad__cultivo').all().order_by('variedad__nombre', 'orden')
        variedad_id = self.kwargs.get('variedad_id') or self.request.query_params.get('variedad')
        if variedad_id:
            qs = qs.filter(variedad_id=variedad_id)
        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        variedad_id = self.kwargs.get('variedad_id') or self.request.query_params.get('variedad') or self.request.data.get('variedad')
        if variedad_id:
            try:
                ctx['variedad'] = Variedad.objects.get(pk=variedad_id)
            except Variedad.DoesNotExist:
                ctx['variedad'] = None
        return ctx

    def perform_create(self, serializer):
        variedad_id = self.kwargs.get('variedad_id') or self.request.data.get('variedad')
        if not variedad_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"variedad": "Crea la etapa usando POST /variedades/{variedad_id}/etapas/ o incluye 'variedad' en el body."})
        try:
            variedad = Variedad.objects.get(pk=variedad_id)
        except Variedad.DoesNotExist:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"variedad": "Variedad no existe."})
        serializer.save(variedad=variedad)


@extend_schema_view(
    get=extend_schema(tags=['etapas'], summary='Detalle de etapa'),
    put=extend_schema(tags=['etapas'], summary='Actualizar etapa'),
    patch=extend_schema(tags=['etapas'], summary='Actualizar parcialmente etapa'),
    delete=extend_schema(tags=['etapas'], summary='Eliminar etapa'),
)
class EtapaDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Recuperar, actualizar o eliminar una etapa.
    """
    queryset = Etapa.objects.select_related('variedad__cultivo').all()
    serializer_class = EtapaSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), HasOperationPermission('etapas', 'ver')]
        if self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), HasOperationPermission('etapas', 'actualizar')]
        if self.request.method == 'DELETE':
            return [permissions.IsAuthenticated(), HasOperationPermission('etapas', 'eliminar')]
        return [permissions.IsAuthenticated()]


@extend_schema_view(
    get=extend_schema(tags=['reglas'], summary='Listar reglas'),
)
class ReglaListView(generics.ListAPIView):
    """
    Listar todas las reglas con filtros opcionales (etapa/variedad/cultivo).
    """
    serializer_class = ReglaPorEtapaSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('reglas', 'ver')]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'reglas', 'ver'):
            return ReglaPorEtapa.objects.none()
        qs = ReglaPorEtapa.objects.select_related('etapa__variedad__cultivo').all().order_by('-prioridad', 'id')
        etapa_id = self.request.query_params.get('etapa')
        variedad_id = self.request.query_params.get('variedad')
        cultivo_id = self.request.query_params.get('cultivo')
        if etapa_id:
            qs = qs.filter(etapa_id=etapa_id)
        if variedad_id:
            qs = qs.filter(etapa__variedad_id=variedad_id)
        if cultivo_id:
            qs = qs.filter(etapa__variedad__cultivo_id=cultivo_id)
        return qs


@extend_schema_view(
    get=extend_schema(tags=['reglas'], summary='Listar reglas por etapa'),
    post=extend_schema(tags=['reglas'], summary='Crear regla para etapa'),
)
class EtapaReglaListCreateView(generics.ListCreateAPIView):
    """
    Listar/crear reglas anidadas por etapa: POST requiere etapa_id en URL.
    """
    serializer_class = ReglaPorEtapaSerializer

    def get_permissions(self):
        op = 'ver' if self.request.method == 'GET' else 'crear'
        return [permissions.IsAuthenticated(), HasOperationPermission('reglas', op)]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'reglas', 'ver'):
            return ReglaPorEtapa.objects.none()
        qs = ReglaPorEtapa.objects.select_related('etapa__variedad__cultivo').all().order_by('-prioridad', 'id')
        etapa_id = self.kwargs.get('etapa_id') or self.request.query_params.get('etapa')
        variedad_id = self.request.query_params.get('variedad')
        cultivo_id = self.request.query_params.get('cultivo')
        if etapa_id:
            qs = qs.filter(etapa_id=etapa_id)
        if variedad_id:
            qs = qs.filter(etapa__variedad_id=variedad_id)
        if cultivo_id:
            qs = qs.filter(etapa__variedad__cultivo_id=cultivo_id)
        return qs

    def perform_create(self, serializer):
        etapa_id = self.kwargs.get('etapa_id') or self.request.data.get('etapa')
        if not etapa_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"etapa": "Crea la regla usando POST /etapas/{etapa_id}/reglas/ o incluye 'etapa' en el body."})
        try:
            etapa = Etapa.objects.get(pk=etapa_id)
        except Etapa.DoesNotExist:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"etapa": "Etapa no existe."})
        serializer.save(created_by=self.request.user, etapa=etapa)


@extend_schema_view(
    get=extend_schema(tags=['reglas'], summary='Detalle de regla'),
    put=extend_schema(tags=['reglas'], summary='Actualizar regla'),
    patch=extend_schema(tags=['reglas'], summary='Actualizar parcialmente regla'),
    delete=extend_schema(tags=['reglas'], summary='Eliminar regla'),
)
class ReglaDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Recuperar, actualizar o eliminar una regla por id.
    """
    queryset = ReglaPorEtapa.objects.select_related('etapa__variedad__cultivo').all()
    serializer_class = ReglaPorEtapaSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), HasOperationPermission('reglas', 'ver')]
        if self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), HasOperationPermission('reglas', 'actualizar')]
        if self.request.method == 'DELETE':
            return [permissions.IsAuthenticated(), HasOperationPermission('reglas', 'eliminar')]
        return [permissions.IsAuthenticated()]