from datetime import datetime
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from drf_spectacular.utils import (
    extend_schema, OpenApiParameter, OpenApiTypes, OpenApiExample
)
from users.permissions import HasOperationPermission, role_name
from .permissions import tiene_permiso, OwnsObjectOrAdmin
from .models import Task
from .serializers import TaskSerializer
from parcels.models import Parcela

@extend_schema(
    tags=['Tareas'],
    summary='Listar / crear tareas (global)',
    description=(
        "GET /tareas/:\n"
        "- Devuelve la lista global de tareas.\n"
        "- Admin/Superadmin/Técnico: ven todas las tareas.\n"
        "- Agricultor: solo tareas pertenecientes a sus parcelas.\n\n"
        "POST /tareas/:\n"
        "- Crea una nueva tarea. Body JSON esperado:\n"
        "  { \"parcela_id\": <int>, \"tipo\": <str>, \"descripcion\": <str>, \"fecha_programada\": <iso-datetime>, \"estado\": <str>, \"origen\": <'manual'|'ia'>, \"recomendacion_id\": <int?> }\n"
        "- Requiere permiso 'tareas.crear' y ser propietario de la parcela (o rol admin/tecnico).\n\n"
        "Respuestas:\n"
        "- 200: lista de tareas\n"
        "- 201: objeto creado\n"
        "- 400/403/404 según validación/permisos/recursos\n"
    ),
    parameters=[
        OpenApiParameter(name='ordering', description='Ordenar por campo (ej: created_at)', required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name='estado', description='Filtrar por estado', required=False, type=OpenApiTypes.STR),
    ],
    request=TaskSerializer,
    responses={200: TaskSerializer(many=True), 201: TaskSerializer},
    examples=[
        OpenApiExample(
            "Lista ejemplo",
            summary="Respuesta ejemplo GET /tareas/",
            value=[{
                "id": 10,
                "parcela_id": 5,
                "recomendacion_id": None,
                "tipo": "riego",
                "descripcion": "Regar sector norte 20 minutos",
                "fecha_programada": "2025-10-25T07:00:00Z",
                "estado": "pendiente",
                "origen": "manual",
                "created_at": "2025-10-20T12:00:00Z",
                "updated_at": "2025-10-20T12:00:00Z"
            }]
        ),
        OpenApiExample(
            "Crear ejemplo",
            summary="Body ejemplo POST /tareas/",
            value={
                "parcela_id": 5,
                "recomendacion_id": None,
                "tipo": "riego",
                "descripcion": "Regar sector norte 20 minutos",
                "fecha_programada": "2025-10-25T07:00:00Z",
                "estado": "pendiente",
                "origen": "manual"
            },
            request_only=True
        )
    ],
)
class TaskListCreateView(generics.ListCreateAPIView):
    queryset = Task.objects.select_related('parcela', 'recomendacion').all().order_by('-created_at')
    serializer_class = TaskSerializer

    def get_permissions(self):
        op = 'ver' if self.request.method == 'GET' else 'crear'
        return [permissions.IsAuthenticated(), HasOperationPermission('tareas', op)]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'tareas', 'ver'):
            raise PermissionDenied("No tienes permiso para ver tareas.")
        qs = self.queryset
        if role_name(user) in ['superadmin', 'administrador', 'tecnico']:
            return qs
        return qs.filter(parcela__usuario=user)

    def perform_create(self, serializer):
        user = self.request.user
        if not tiene_permiso(user, 'tareas', 'crear'):
            raise PermissionDenied("No tienes permiso para crear tareas.")
        parcela_id = self.request.data.get('parcela_id')
        if not parcela_id:
            raise ValidationError({"parcela_id": "parcela_id es requerido."})
        try:
            parcela = Parcela.objects.get(pk=parcela_id)
        except Parcela.DoesNotExist:
            raise NotFound("Parcela no encontrada.")
        if role_name(user) not in ['superadmin', 'administrador', 'tecnico'] and parcela.usuario != user:
            raise PermissionDenied("No puedes crear tareas en parcelas que no son tuyas.")
        serializer.save(parcela=parcela)


@extend_schema(
    tags=['Tareas'],
    summary='Listar / crear tareas por parcela',
    description=(
        "Operaciones enfocadas a una parcela específica.\n\n"
        "- GET /parcelas/{parcela_id}/tareas/: listado histórico de tareas para la parcela.\n"
        "- POST /parcelas/{parcela_id}/tareas/: crear tarea asociada a la parcela indicada.\n\n"
        "Acceso:\n- Admin/Superadmin/Técnico: acceso a cualquier parcela.\n- Agricultor: solo a sus parcelas.\n"
    ),
    parameters=[
        OpenApiParameter(name='parcela_id', description='ID de la parcela', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH),
    ],
    request=TaskSerializer,
    responses={200: TaskSerializer(many=True), 201: TaskSerializer},
    examples=[
        OpenApiExample(
            "Lista parcela ejemplo",
            value=[{
                "id": 12,
                "parcela_id": 7,
                "recomendacion_id": 3,
                "tipo": "fertilizacion",
                "descripcion": "Aplicar fertilizante NPK 10-10-10",
                "fecha_programada": "2025-11-01T08:00:00Z",
                "estado": "pendiente",
                "origen": "ia",
                "created_at": "2025-10-20T12:00:00Z",
                "updated_at": "2025-10-20T12:00:00Z"
            }]
        )
    ]
)
class TaskByParcelaListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer

    def get_permissions(self):
        op = 'ver' if self.request.method == 'GET' else 'crear'
        return [permissions.IsAuthenticated(), HasOperationPermission('tareas', op)]

    def get_parcela_or_404(self, parcela_id):
        try:
            return Parcela.objects.get(pk=parcela_id)
        except Parcela.DoesNotExist:
            raise NotFound("Parcela no existe.")

    def get_queryset(self):
        user = self.request.user
        parcela = self.get_parcela_or_404(self.kwargs.get('parcela_id'))
        if not tiene_permiso(user, 'tareas', 'ver'):
            raise PermissionDenied("No tienes permiso para ver tareas.")
        if role_name(user) in ['superadmin', 'administrador', 'tecnico'] or parcela.usuario == user:
            return Task.objects.filter(parcela=parcela).order_by('-created_at')
        raise PermissionDenied("No tienes permiso para ver las tareas de esta parcela.")

    def perform_create(self, serializer):
        user = self.request.user
        parcela = self.get_parcela_or_404(self.kwargs.get('parcela_id'))
        if not tiene_permiso(user, 'tareas', 'crear'):
            raise PermissionDenied("No tienes permiso para crear tareas.")
        if role_name(user) not in ['superadmin', 'administrador', 'tecnico'] and parcela.usuario != user:
            raise PermissionDenied("No puedes crear tareas en esta parcela.")
        serializer.save(parcela=parcela)


@extend_schema(
    tags=['Tareas'],
    summary='Detalle / actualizar / eliminar tarea',
    description=(
        "Operaciones sobre una tarea individual.\n\n"
        "- GET /tareas/{pk}/: recuperar tarea.\n"
        "- PUT/PATCH /tareas/{pk}/: actualizar tarea (requiere permiso 'tareas.actualizar').\n"
        "- DELETE /tareas/{pk}/: eliminar tarea (requiere permiso 'tareas.eliminar').\n\n"
        "Acceso: admin/tecnico/superadmin o propietario de la parcela asociada.\n"
    ),
    parameters=[
        OpenApiParameter(name='pk', description='ID de la tarea', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH),
    ],
    request=TaskSerializer,
    responses={200: TaskSerializer, 204: None},
    examples=[
        OpenApiExample(
            "Detalle ejemplo",
            value={
                "id": 12,
                "parcela_id": 7,
                "recomendacion_id": 3,
                "tipo": "fertilizacion",
                "descripcion": "Aplicar fertilizante NPK 10-10-10",
                "fecha_programada": "2025-11-01T08:00:00Z",
                "estado": "pendiente",
                "origen": "ia",
                "created_at": "2025-10-20T12:00:00Z",
                "updated_at": "2025-10-20T12:00:00Z"
            }
        )
    ]
)
class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), HasOperationPermission('tareas', 'ver'), OwnsObjectOrAdmin()]
        if self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), HasOperationPermission('tareas', 'actualizar'), OwnsObjectOrAdmin()]
        if self.request.method == 'DELETE':
            return [permissions.IsAuthenticated(), HasOperationPermission('tareas', 'eliminar'), OwnsObjectOrAdmin()]
        return [permissions.IsAuthenticated()]

    def get_object(self):
        user = self.request.user
        pk = self.kwargs.get('pk')
        try:
            obj = Task.objects.select_related('parcela').get(pk=pk)
        except Task.DoesNotExist:
            raise NotFound("Tarea no encontrada.")
        if not tiene_permiso(user, 'tareas', 'ver'):
            raise PermissionDenied("No tienes permiso para ver tareas.")
        if role_name(user) in ['superadmin', 'administrador', 'tecnico']:
            return obj
        if getattr(obj.parcela, 'usuario', None) == user:
            return obj
        raise PermissionDenied("No tienes permiso sobre esta tarea.")