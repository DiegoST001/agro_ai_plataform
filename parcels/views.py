from django.db.models import Count
from rest_framework import permissions, generics
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter, OpenApiTypes, OpenApiExample
from users.permissions import HasOperationPermission, OwnsObjectOrAdmin, role_name, tiene_permiso
from .models import Parcela, Cultivo, Variedad
from .serializers import (
    ParcelaCreateSerializer,
    ParcelaUpdateSerializer,
    ParcelaAdminListSerializer,
    ParcelaOwnerListSerializer,
    CultivoSerializer,
    VariedadSerializer,
    CultivoSimpleSerializer,
    VariedadSimpleSerializer,
)

def _annotate_parcelas(qs):
    return qs.select_related('usuario').annotate(
        nodos_maestros_count=Count('nodos_maestros', distinct=True),
        nodos_secundarios_count=Count('nodos_maestros__secundarios', distinct=True),
    )

@extend_schema_view(
    get=extend_schema(
        tags=['parcelas'],
        summary='Listar parcelas',
        description=(
            "Devuelve una lista de parcelas.\n\n"
            "- **Admin/Superadmin/Técnico:** ven todas las parcelas, incluyendo el usuario propietario y contadores de nodos.\n"
            "- **Agricultor:** solo ve sus propias parcelas, sin campo usuario, pero con contadores de nodos.\n"
            "- Los nodos no se anidan, solo se muestran los conteos.\n\n"
            "**Parámetros:**\n"
            "- `ubicacion`: filtra por ubicación\n"
            "- `search`: busca por nombre o ubicación\n"
            "- `ordering`: ordena por campo\n\n"
            "**Respuesta ejemplo:**\n"
            "```json\n"
            "[{\n"
            "  \"id\": 51,\n"
            "  \"nombre\": \"Parcela Agri2 2\",\n"
            "  \"ubicacion\": \"Costa Sur\",\n"
            "  \"tamano_hectareas\": \"15.00\",\n"
            "  \"latitud\": \"-16.409047\",\n"
            "  \"longitud\": \"-71.537451\",\n"
            "  \"altitud\": \"200.00\",\n"
            "  \"created_at\": \"2025-10-20T05:01:35.153540Z\",\n"
            "  \"updated_at\": \"2025-10-20T05:01:35.153548Z\",\n"
            "  \"cultivo\": {\"id\": 1, \"nombre\": \"Papaya\", \"variedad\": {\"id\": 2, \"nombre\": \"Red Lady\"}},\n"
            "  \"nodos_maestros_count\": 1,\n"
            "  \"nodos_secundarios_count\": 3\n"
            "}]"
            "```"
        ),
        parameters=[
            OpenApiParameter(name='ubicacion', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="Filtrar por ubicación"),
            OpenApiParameter(name='search', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="Buscar por nombre o ubicación"),
            OpenApiParameter(name='ordering', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="Ordenar por campo"),
        ],
        responses={200: ParcelaAdminListSerializer(many=True)},
        examples=[
            OpenApiExample(
                'Lista de parcelas',
                value=[{
                    "id": 51,
                    "nombre": "Parcela Agri2 2",
                    "ubicacion": "Costa Sur",
                    "tamano_hectareas": "15.00",
                    "latitud": "-16.409047",
                    "longitud": "-71.537451",
                    "altitud": "200.00",
                    "created_at": "2025-10-20T05:01:35.153540Z",
                    "updated_at": "2025-10-20T05:01:35.153548Z",
                    "cultivo": {
                        "id": 1,
                        "nombre": "Papaya",
                        "variedad": {
                            "id": 2,
                            "nombre": "Red Lady"
                        }
                    },
                    "nodos_maestros_count": 1,
                    "nodos_secundarios_count": 3
                }]
            )
        ]
    ),
    post=extend_schema(
        tags=['parcelas'],
        summary='Crear parcela',
        description=(
            "Crea una nueva parcela y la asigna al usuario autenticado.\n"
            "- El usuario no se puede especificar, se asigna automáticamente.\n"
            "- Requiere permiso de creación en el módulo 'parcelas'.\n\n"
            "**Campos requeridos:** nombre, cultivo, variedad\n"
            "**Ejemplo de solicitud:**\n"
            "```json\n"
            "{\n"
            "  \"nombre\": \"Parcela Nueva\",\n"
            "  \"ubicacion\": \"Valle\",\n"
            "  \"tamano_hectareas\": 10.5,\n"
            "  \"latitud\": -12.0,\n"
            "  \"longitud\": -77.0,\n"
            "  \"altitud\": 100.0,\n"
            "  \"cultivo\": 1,\n"
            "  \"variedad\": 2\n"
            "}\n"
            "```"
        ),
        request=ParcelaCreateSerializer,
        responses={201: ParcelaAdminListSerializer},
        examples=[
            OpenApiExample(
                'Crear parcela',
                value={
                    "nombre": "Parcela Nueva",
                    "ubicacion": "Valle",
                    "tamano_hectareas": 10.5,
                    "latitud": -12.0,
                    "longitud": -77.0,
                    "altitud": 100.0,
                    "cultivo": 1,
                    "variedad": 2
                }
            )
        ]
    ),
)
class ParcelaListCreateView(generics.ListCreateAPIView):
    queryset = Parcela.objects.all()
    filterset_fields = ['ubicacion', 'latitud', 'longitud']
    search_fields = ['nombre', 'ubicacion']
    ordering_fields = ['created_at', 'nombre', 'tamano_hectareas']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'parcelas', 'ver'):
            return Parcela.objects.none()
        r = role_name(user)
        base = _annotate_parcelas(Parcela.objects.all())
        if r in ['superadmin', 'administrador', 'tecnico']:
            return base
        if r == 'agricultor':
            return base.filter(usuario=user)
        return Parcela.objects.none()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ParcelaCreateSerializer
        r = role_name(self.request.user)
        return ParcelaAdminListSerializer if r in ['superadmin', 'administrador', 'tecnico'] else ParcelaOwnerListSerializer

    def get_permissions(self):
        base = [permissions.IsAuthenticated()]
        base.append(HasOperationPermission('parcelas', 'ver' if self.request.method == 'GET' else 'crear'))
        return base

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

@extend_schema_view(
    get=extend_schema(
        tags=['parcelas'],
        summary='Detalle de parcela',
        description=(
            "Devuelve el detalle de una parcela.\n\n"
            "- **Admin/Superadmin/Técnico:** pueden consultar cualquier parcela.\n"
            "- **Agricultor:** solo puede consultar parcelas propias.\n"
            "- Requiere permiso de 'ver' en el módulo 'parcelas'."
        ),
        responses={200: ParcelaUpdateSerializer},
        examples=[
            OpenApiExample(
                'Detalle de parcela',
                value={
                    "id": 51,
                    "nombre": "Parcela Agri2 2",
                    "ubicacion": "Costa Sur",
                    "tamano_hectareas": "15.00",
                    "latitud": "-16.409047",
                    "longitud": "-71.537451",
                    "altitud": "200.00",
                    "created_at": "2025-10-20T05:01:35.153540Z",
                    "updated_at": "2025-10-20T05:01:35.153548Z",
                    "cultivo": {
                        "id": 1,
                        "nombre": "Papaya",
                        "variedad": {
                            "id": 2,
                            "nombre": "Red Lady"
                        }
                    }
                }
            )
        ]
    ),
    patch=extend_schema(
        tags=['parcelas'],
        summary='Editar parcialmente parcela',
        description=(
            "Permite editar parcialmente una parcela.\n"
            "- Solo el propietario o admin/superadmin pueden editar.\n"
            "- Requiere permiso de 'actualizar' en el módulo 'parcelas'."
        ),
        request=ParcelaUpdateSerializer,
        responses={200: ParcelaUpdateSerializer},
    ),
    put=extend_schema(
        tags=['parcelas'],
        summary='Editar parcela',
        description=(
            "Permite editar todos los campos de una parcela.\n"
            "- Solo el propietario o admin/superadmin pueden editar.\n"
            "- Requiere permiso de 'actualizar' en el módulo 'parcelas'."
        ),
        request=ParcelaUpdateSerializer,
        responses={200: ParcelaUpdateSerializer},
    ),
    delete=extend_schema(
        tags=['parcelas'],
        summary='Eliminar parcela',
        description=(
            "Elimina una parcela.\n"
            "- Solo el propietario o admin/superadmin pueden eliminar.\n"
            "- Requiere permiso de 'eliminar' en el módulo 'parcelas'."
        ),
        responses={204: None},
    ),
)
class ParcelaDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ParcelaUpdateSerializer
    owner_path = 'usuario'

    def _op(self):
        if self.request.method == 'GET':
            return 'ver'
        if self.request.method in ['PUT', 'PATCH']:
            return 'actualizar'
        if self.request.method == 'DELETE':
            return 'eliminar'
        return 'ver'

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'parcelas', self._op()):
            return Parcela.objects.none()
        r = role_name(user)
        qs = Parcela.objects.select_related('usuario')
        if r in ['superadmin', 'administrador', 'tecnico']:
            return qs
        if r == 'agricultor':
            return qs.filter(usuario=user)
        return Parcela.objects.none()

    def get_permissions(self):
        return [
            permissions.IsAuthenticated(),
            HasOperationPermission('parcelas', self._op()),
            OwnsObjectOrAdmin(),
        ]

    def destroy(self, request, *args, **kwargs):
        # get_object aplicará get_queryset() -> puede levantar 404 si no tiene acceso al objeto
        instance = self.get_object()
        # 1) permiso de operación
        if not tiene_permiso(request.user, 'parcelas', 'eliminar'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(detail="Denegado: no tiene permiso de operación 'eliminar' en módulo 'parcelas'.")

        # 2) permiso de propietario/admin
        r = role_name(request.user)
        owner_pk = getattr(getattr(instance, 'usuario', None), 'pk', None)
        if r not in ['superadmin', 'administrador'] and owner_pk != getattr(request.user, 'pk', None):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(detail="Denegado: solo el propietario o administrador puede eliminar esta parcela.")

        # 3) eliminar
        instance.delete()
        from rest_framework.response import Response
        return Response(status=204)

@extend_schema_view(
    get=extend_schema(
        tags=['parcelas'],
        summary='Listar todas las parcelas (admin)',
        description=(
            "Endpoint solo para administradores/superadmins.\n"
            "Devuelve todas las parcelas, permite filtrar por usuario y ubicación.\n"
            "Incluye contadores de nodos y datos del usuario propietario."
        ),
        parameters=[
            OpenApiParameter(name='usuario', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, description="Filtrar por usuario"),
            OpenApiParameter(name='ubicacion', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="Filtrar por ubicación"),
            OpenApiParameter(name='search', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="Buscar por nombre/ubicación/usuario"),
            OpenApiParameter(name='ordering', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="Ordenar por campo"),
        ],
        responses={200: ParcelaAdminListSerializer(many=True)},
        examples=[
            OpenApiExample(
                'Lista admin',
                value=[{
                    "id": 51,
                    "nombre": "Parcela Agri2 2",
                    "usuario": {"id": 8, "username": "agricultor2", "email": "agri2@demo.com"},
                    "ubicacion": "Costa Sur",
                    "tamano_hectareas": "15.00",
                    "latitud": "-16.409047",
                    "longitud": "-71.537451",
                    "altitud": "200.00",
                    "created_at": "2025-10-20T05:01:35.153540Z",
                    "updated_at": "2025-10-20T05:01:35.153548Z",
                    "cultivo": {
                        "id": 1,
                        "nombre": "Papaya",
                        "variedad": {
                            "id": 2,
                            "nombre": "Red Lady"
                        }
                    },
                    "nodos_maestros_count": 1,
                    "nodos_secundarios_count": 3
                }]
            )
        ]
    ),
)
class AdminParcelaListView(generics.ListAPIView):
    serializer_class = ParcelaAdminListSerializer
    queryset = _annotate_parcelas(Parcela.objects.all())
    filterset_fields = ['usuario', 'ubicacion']
    search_fields = ['nombre', 'ubicacion', 'usuario__username']
    ordering_fields = ['created_at', 'nombre', 'tamano_hectareas']
    ordering = ['-created_at']

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('administracion', 'ver')]

@extend_schema_view(
    get=extend_schema(
        tags=['parcelas'],
        summary='Detalle de parcela (admin)',
        description=(
            "Devuelve el detalle de una parcela para administradores/superadmins.\n"
            "Permite consultar, editar o eliminar cualquier parcela según permisos."
        ),
        responses={200: ParcelaUpdateSerializer},
        examples=[
            OpenApiExample(
                'Detalle admin',
                value={
                    "id": 51,
                    "nombre": "Parcela Agri2 2",
                    "usuario": {"id": 8, "username": "agricultor2", "email": "agri2@demo.com"},
                    "ubicacion": "Costa Sur",
                    "tamano_hectareas": "15.00",
                    "latitud": "-16.409047",
                    "longitud": "-71.537451",
                    "altitud": "200.00",
                    "created_at": "2025-10-20T05:01:35.153540Z",
                    "updated_at": "2025-10-20T05:01:35.153548Z",
                    "cultivo": {
                        "id": 1,
                        "nombre": "Papaya",
                        "variedad": {
                            "id": 2,
                            "nombre": "Red Lady"
                        }
                    }
                }
            )
        ]
    ),
    patch=extend_schema(
        tags=['parcelas'],
        summary='Editar parcialmente parcela (admin)',
        description="Editar parcialmente una parcela como administrador/superadmin.",
        request=ParcelaUpdateSerializer,
        responses={200: ParcelaUpdateSerializer},
    ),
    put=extend_schema(
        tags=['parcelas'],
        summary='Editar parcela (admin)',
        description="Editar todos los campos de una parcela como administrador/superadmin.",
        request=ParcelaUpdateSerializer,
        responses={200: ParcelaUpdateSerializer},
    ),
    delete=extend_schema(
        tags=['parcelas'],
        summary='Eliminar parcela (admin)',
        description="Eliminar una parcela como administrador/superadmin.",
        responses={204: None},
    ),
)
class AdminParcelaDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ParcelaUpdateSerializer
    queryset = Parcela.objects.select_related('usuario').all()

    def get_permissions(self):
        base = [permissions.IsAuthenticated()]
        if self.request.method == 'GET':
            base.append(HasOperationPermission('administracion', 'ver'))
        elif self.request.method in ['PUT', 'PATCH']:
            base.append(HasOperationPermission('administracion', 'actualizar'))
        elif self.request.method == 'DELETE':
            base.append(HasOperationPermission('administracion', 'eliminar'))
        return base

class CultivoListView(generics.ListAPIView):
    """
    Lista de cultivos (para el frontend). Requiere permiso 'ver' en 'parcelas'.
    """
    queryset = Cultivo.objects.all().order_by('nombre')
    serializer_class = CultivoSimpleSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('parcelas', 'ver')]

class VariedadListView(generics.ListAPIView):
    """
    Lista de variedades. Se puede filtrar por ?cultivo=<id>.
    """
    serializer_class = VariedadSimpleSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('parcelas', 'ver')]

    def get_queryset(self):
        qs = Variedad.objects.select_related('cultivo').all().order_by('nombre')
        cultivo_id = self.request.query_params.get('cultivo')
        if cultivo_id:
            qs = qs.filter(cultivo_id=cultivo_id)
        return qs

@extend_schema_view(
    get=extend_schema(tags=['cultivos'], summary='Listar cultivos'),
    post=extend_schema(tags=['cultivos'], summary='Crear cultivo'),
)
class CultivoListCreateView(generics.ListCreateAPIView):
    queryset = Cultivo.objects.all().order_by('nombre')
    serializer_class = CultivoSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('cultivos', 'ver' if self.request.method == 'GET' else 'crear')]

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
    serializer_class = VariedadSerializer

    def get_permissions(self):
        op = 'ver' if self.request.method == 'GET' else 'crear'
        # si la petición es /cultivos/<cultivo_id>/variedades/ usar permiso sobre el módulo 'cultivos'
        if self.kwargs.get('cultivo_id'):
            return [permissions.IsAuthenticated(), HasOperationPermission('cultivos', op)]
        # ruta global /variedades/ usa el módulo 'variedades'
        return [permissions.IsAuthenticated(), HasOperationPermission('variedades', op)]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'variedades', 'ver'):
            return Variedad.objects.none()
        qs = Variedad.objects.select_related('cultivo').all().order_by('cultivo__nombre', 'nombre')
        # Priorizar cultivo_id desde la URL (kwargs), luego query param ?cultivo=
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
            raise ValidationError({"cultivo": "Proporciona cultivo en la URL o en el body."})
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




