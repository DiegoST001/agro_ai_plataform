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
        "Operaciones sobre el recurso Tarea (global).\n\n"
        "GET /api/tareas/:\n"
        "- Devuelve la lista global de tareas del sistema.\n"
        "- Acceso: Admin / Superadmin / Técnico ven todas las tareas; Agricultor solo las tareas de sus parcelas.\n"
        "- Soporta filtros por `estado` y ordenamiento (`ordering`).\n\n"
        "POST /api/tareas/:\n"
        "- Crea una tarea asociada a una parcela.\n"
        "- Cuerpo JSON esperado (ejemplos abajo):\n"
        "  {\n"
        "    \"parcela_id\": <int>,            # id de la parcela (requerido)\n"
        "    \"tipo\": <string>,              # p.ej. 'riego', 'fertilizacion' (requerido)\n"
        "    \"descripcion\": <string>,       # texto descriptivo / puede incluir snapshot\n"
        "    \"fecha_programada\": <datetime>,# ISO-8601\n"
        "    \"estado\": <string>,            # 'pendiente'|'en_progreso'|'completada'|'cancelada'\n"
        "    \"origen\": <'manual'|'ia'>      # 'ia' para recomendaciones generadas por el motor\n"
        "  }\n\n"
        "Notas importantes:\n"
        "- Para `origen='ia'` la tarea se crea con `decision='pendiente'` y requiere que el usuario acepte/rechace.\n"
        "- El sistema define AUTO_REJECT_DAYS = 3: un job programado puede auto-rechazar (soft-delete) recomendaciones IA pendientes después de ese plazo.\n\n"
        "Códigos de respuesta:\n"
        "- 200: lista de tareas\n"
        "- 201: tarea creada\n"
        "- 400: error de validación (p.ej. parcela_id faltante)\n"
        "- 403: permiso denegado\n"
        "- 404: parcela no encontrada\n"
    ),
    parameters=[
        OpenApiParameter(name='ordering', description='Ordenar por campo (ej: created_at, -created_at)', required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name='estado', description='Filtrar por estado (pendiente|en_progreso|completada|cancelada)', required=False, type=OpenApiTypes.STR),
    ],
    request=TaskSerializer,
    responses={
        200: TaskSerializer(many=True),
        201: TaskSerializer,
        400: OpenApiExample('Bad Request', value={"detail": "parcela_id es requerido."}),
        403: OpenApiExample('Forbidden', value={"detail": "No tienes permiso para ver/crear tareas."}),
        404: OpenApiExample('Not Found', value={"detail": "Parcela no encontrada."}),
    },
    examples=[
        OpenApiExample(
            "Lista ejemplo",
            summary="Respuesta ejemplo GET /api/tareas/",
            value=[{
                "id": 10,
                "parcela_id": 5,
                "tipo": "riego",
                "descripcion": "Regar sector norte 20 minutos",
                "fecha_programada": "2025-10-25T07:00:00Z",
                "estado": "pendiente",
                "origen": "manual",
                "decision": "pendiente",
                "created_at": "2025-10-20T12:00:00Z",
                "updated_at": "2025-10-20T12:00:00Z"
            }]
        ),
        OpenApiExample(
            "Crear ejemplo",
            summary="Body ejemplo POST /api/tareas/",
            value={
                "parcela_id": 5,
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
        "Operaciones centradas en las tareas de una parcela específica.\n\n"
        "Rutas:\n"
        "- GET /api/parcelas/{parcela_id}/tareas/: devuelve el historial de tareas de la parcela.\n"
        "- POST /api/parcelas/{parcela_id}/tareas/: crea una tarea ligada a la parcela indicada (NO incluir parcela_id en el body; el id se toma de la URL).\n\n"
        "Acceso:\n"
        "- Admin / Superadmin / Técnico: acceso completo.\n"
        "- Agricultor: solo si es propietario de la parcela.\n\n"
        "Cuerpo/Respuesta: mismo esquema que en el endpoint global, salvo que para POST el campo parcela_id no es necesario (y se ignora si está presente).\n"
    ),
    parameters=[
        OpenApiParameter(name='parcela_id', description='ID de la parcela (path)', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH),
    ],
    request=TaskSerializer,
    responses={
        200: TaskSerializer(many=True),
        201: TaskSerializer,
        403: OpenApiExample('Forbidden', value={"detail": "No tienes permiso para ver/crear tareas en esta parcela."}),
        404: OpenApiExample('Not Found', value={"detail": "Parcela no existe."}),
    },
    examples=[
        OpenApiExample(
            "Lista parcela ejemplo",
            summary="GET /api/parcelas/{parcela_id}/tareas/ ejemplo",
            value=[{
                "id": 12,
                "parcela_id": 7,
                "tipo": "fertilizacion",
                "descripcion": "Aplicar fertilizante NPK 10-10-10",
                "fecha_programada": "2025-11-01T08:00:00Z",
                "estado": "pendiente",
                "origen": "ia",
                "decision": "pendiente",
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
        "Operaciones sobre una tarea individual identificada por su id (pk).\n\n"
        "- GET /api/tareas/{pk}/: recuperar datos completos de la tarea.\n"
        "- PUT/PATCH /api/tareas/{pk}/: actualizar (requiere 'tareas.actualizar').\n"
        "- DELETE /api/tareas/{pk}/: eliminar (requiere 'tareas.eliminar').\n\n"
        "Permisos y acceso:\n"
        "- Admin / Superadmin / Técnico: acceso a cualquier tarea.\n"
        "- Agricultor: solo si es propietario de la parcela vinculada.\n\n"
        "Comportamiento especial para recomendaciones IA:\n"
        "- Si la tarea tiene `origen='ia'` aparecerá con `decision='pendiente'` hasta que el usuario la acepte (decision='aceptada') o la rechace (decision='rechazada').\n"
        "- Un job programado puede usar AUTO_REJECT_DAYS para auto-rechazar (soft-delete) recomendaciones IA pendientes tras ese periodo.\n\n"
        "Respuestas:\n"
        "- 200: objeto tarea\n"
        "- 204: eliminado\n"
        "- 403/404 según permisos o recurso\n"
    ),
    parameters=[
        OpenApiParameter(name='pk', description='ID de la tarea', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH),
    ],
    request=TaskSerializer,
    responses={
        200: TaskSerializer,
        204: None,
        403: OpenApiExample('Forbidden', value={"detail": "No tienes permiso sobre esta tarea."}),
        404: OpenApiExample('Not Found', value={"detail": "Tarea no encontrada."}),
    },
    examples=[
        OpenApiExample(
            "Detalle ejemplo",
            value={
                "id": 12,
                "parcela_id": 7,
                "tipo": "fertilizacion",
                "descripcion": "Aplicar fertilizante NPK 10-10-10",
                "fecha_programada": "2025-11-01T08:00:00Z",
                "estado": "pendiente",
                "origen": "ia",
                "decision": "pendiente",
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