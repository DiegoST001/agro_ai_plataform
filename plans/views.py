from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, OpenApiTypes
from users.permissions import HasOperationPermission, role_name
from .models import Plan, ParcelaPlan
from .serializers import PlanSerializer, ParcelaPlanSerializer
from parcels.models import Parcela
from .permissions import tiene_permiso  # adapter that reuses users.permissions

#
# Plans (CRUD)
#
@extend_schema(
    tags=['Planes'],
    summary='Listar / crear planes',
    description=(
        "GET: Devuelve la lista de planes disponibles ordenados por precio.\n\n"
        "POST: Crear un nuevo plan. Requiere permiso 'planes.crear'.\n\n"
        "Permisos:\n"
        "- GET: requiere permiso 'planes.ver'.\n"
        "- POST: requiere permiso 'planes.crear'.\n\n"
        "Campos Plan (ejemplo): nombre, descripcion, veces_por_dia, horarios_por_defecto, precio"
    ),
    parameters=[
        OpenApiParameter(name='ordering', description='Ordenar por campo (ej: precio)', required=False, type=OpenApiTypes.STR),
    ],
    request=PlanSerializer,
    responses={200: PlanSerializer(many=True), 201: PlanSerializer},
    examples=[
        OpenApiExample(
            'Lista ejemplo',
            description='Respuesta ejemplo de GET /planes/',
            value=[{
                "id": 1,
                "nombre": "Básico",
                "descripcion": "Plan básico",
                "veces_por_dia": 3,
                "horarios_por_defecto": ["07:00","15:00","22:00"],
                "precio": "9.99",
                "created_at": "2025-10-20T00:00:00Z",
                "updated_at": "2025-10-20T00:00:00Z"
            }]
        ),
        OpenApiExample(
            'Crear ejemplo',
            description='Body ejemplo para POST /planes/',
            value={
                "nombre": "Pro",
                "descripcion": "Plan pro",
                "veces_por_dia": 6,
                "horarios_por_defecto": ["06:00","12:00","18:00","00:00","04:00","20:00"],
                "precio": "29.99"
            },
            request_only=True
        )
    ]
)
class PlanListCreateView(generics.ListCreateAPIView):
    queryset = Plan.objects.all().order_by('precio')
    serializer_class = PlanSerializer

    def get_permissions(self):
        # GET -> ver, POST -> crear
        op = 'ver' if self.request.method == 'GET' else 'crear'
        return [permissions.IsAuthenticated(), HasOperationPermission('planes', op)]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'planes', 'ver'):
            raise PermissionDenied("No tienes permiso para ver planes.")
        return self.queryset

    def perform_create(self, serializer):
        user = self.request.user
        if not tiene_permiso(user, 'planes', 'crear'):
            raise PermissionDenied("No tienes permiso para crear planes.")
        serializer.save()

@extend_schema(
    tags=['Planes'],
    summary='Detalle / actualizar / eliminar plan',
    description=(
        "Recupera, actualiza o elimina un plan por su id.\n\n"
        "- GET: devuelve el plan.\n"
        "- PUT/PATCH: actualiza el plan (requiere 'planes.actualizar').\n"
        "- DELETE: elimina el plan (requiere 'planes.eliminar')."
    ),
    request=PlanSerializer,
    responses={200: PlanSerializer, 204: None},
    examples=[
        OpenApiExample(
            'Detalle ejemplo',
            value={
                "id": 1,
                "nombre": "Básico",
                "descripcion": "Plan básico",
                "veces_por_dia": 3,
                "horarios_por_defecto": ["07:00","15:00","22:00"],
                "precio": "9.99",
                "created_at": "2025-10-20T00:00:00Z",
                "updated_at": "2025-10-20T00:00:00Z"
            }
        )
    ]
)
class PlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), HasOperationPermission('planes', 'ver')]
        if self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), HasOperationPermission('planes', 'actualizar')]
        if self.request.method == 'DELETE':
            return [permissions.IsAuthenticated(), HasOperationPermission('planes', 'eliminar')]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'planes', 'ver'):
            raise PermissionDenied("No tienes permiso para ver planes.")
        return Plan.objects.all()

#
# ParcelaPlan (suscripciones)
#
@extend_schema(
    tags=['Planes'],
    summary='Listar suscripciones de una parcela',
    description=(
        "Devuelve las suscripciones (histórico) asociadas a una parcela.\n\n"
        "- Admin/Superadmin: pueden listar las suscripciones de cualquier parcela.\n"
        "- Agricultor: solo sus propias parcelas.\n\n"
        "Parámetros:\n- parcela_id (ruta): id de la parcela.\n"
    ),
    parameters=[
        OpenApiParameter(name='parcela_id', description='ID de la parcela', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH)
    ],
    responses={200: ParcelaPlanSerializer(many=True)}
)
class ParcelaPlanListView(generics.ListCreateAPIView):
    serializer_class = ParcelaPlanSerializer

    def get_permissions(self):
        # GET -> ver, POST -> crear
        op = 'ver' if self.request.method == 'GET' else 'crear'
        return [permissions.IsAuthenticated(), HasOperationPermission('planes', op)]

    def get_queryset(self):
        user = self.request.user
        parcela_id = self.kwargs.get('parcela_id')
        # existir parcela -> 404
        try:
            parcela = Parcela.objects.get(pk=parcela_id)
        except Parcela.DoesNotExist:
            raise NotFound("Parcela no existe.")
        # permiso de módulo
        if not tiene_permiso(user, 'planes', 'ver'):
            raise PermissionDenied("No tienes permiso para ver planes.")
        # admin puede ver todo
        if role_name(user) in ['superadmin', 'administrador']:
            return ParcelaPlan.objects.filter(parcela=parcela).order_by('-fecha_inicio')
        # propietario solo sus parcelas
        if parcela.usuario == user:
            return ParcelaPlan.objects.filter(parcela=parcela).order_by('-fecha_inicio')
        raise PermissionDenied("No tienes permiso para ver las suscripciones de esta parcela.")

    def perform_create(self, serializer):
        user = self.request.user
        parcela_id = self.kwargs.get('parcela_id')
        try:
            parcela = Parcela.objects.get(pk=parcela_id)
        except Parcela.DoesNotExist:
            raise NotFound("Parcela no existe.")

        if not tiene_permiso(user, 'planes', 'crear'):
            raise PermissionDenied("No tienes permiso para crear suscripciones de plan.")

        if role_name(user) not in ['superadmin', 'administrador'] and parcela.usuario != user:
            raise PermissionDenied("No puedes cambiar el plan de una parcela que no es tuya.")

        plan = serializer.validated_data.get('plan')
        if not plan:
            raise ValidationError({"plan_id": "plan_id es requerido."})

        fecha_inicio = serializer.validated_data.get('fecha_inicio')  # puede ser None

        # si ya existe un plan activo
        activo = ParcelaPlan.objects.filter(parcela=parcela, estado='activo').first()
        if activo:
            # determinar fecha de fin efectiva del plan activo
            if activo.fecha_fin:
                activo_end = activo.fecha_fin
            else:
                # fallback: si activo no tiene fecha_fin, asumir un mes desde su fecha_inicio
                activo_end = (activo.fecha_inicio + relativedelta(months=1)) if activo.fecha_inicio else (date.today() + timedelta(days=30))

            earliest_start = activo_end + timedelta(days=1)

            if fecha_inicio:
                # si se proporcionó fecha_inicio, debe ser posterior al fin del activo
                if fecha_inicio <= activo_end:
                    raise ValidationError({
                        "detail": (
                            f"Ya existe un plan activo hasta {activo_end.isoformat()}. "
                            f"Indica 'fecha_inicio' >= {earliest_start.isoformat()} o deja vacío para programarlo automáticamente desde {earliest_start.isoformat()}."
                        )
                    })
                # fecha_inicio válida -> programado
                estado = 'programado'
                serializer.save(parcela=parcela, fecha_inicio=fecha_inicio, estado=estado)
                return
            else:
                # sin fecha_inicio -> programar automáticamente para empezar después del plan activo
                estado = 'programado'
                serializer.save(parcela=parcela, fecha_inicio=earliest_start, estado=estado)
                return

        # no hay plan activo -> crear activo o programado según fecha_inicio
        if fecha_inicio and fecha_inicio > date.today():
            estado = 'programado'
            fecha = fecha_inicio
        else:
            estado = 'activo'
            fecha = fecha_inicio if fecha_inicio else date.today()

        serializer.save(parcela=parcela, fecha_inicio=fecha, estado=estado)

@extend_schema(
    tags=['Planes'],
    summary='Detalle / eliminar / actualizar suscripción (admin/owner)',
    description=(
        "Recupera, actualiza o elimina una suscripción (ParcelaPlan).\n\n"
        "- GET: devuelve la suscripción.\n"
        "- PUT/PATCH: actualizar (requiere 'planes.actualizar').\n"
        "- DELETE: eliminar (requiere 'planes.eliminar').\n\n"
        "Acceso: admin/superadmin o propietario de la parcela."
    ),
    request=ParcelaPlanSerializer,
    responses={200: ParcelaPlanSerializer, 204: None},
    parameters=[
        OpenApiParameter(name='pk', description='ID de la suscripción (ParcelaPlan)', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH)
    ]
)
class ParcelaPlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ParcelaPlanSerializer

    def get_permissions(self):
        # GET -> ver (planes), UPDATE -> actualizar, DELETE -> eliminar
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), HasOperationPermission('planes', 'ver')]
        if self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), HasOperationPermission('planes', 'actualizar')]
        if self.request.method == 'DELETE':
            return [permissions.IsAuthenticated(), HasOperationPermission('planes', 'eliminar')]
        return [permissions.IsAuthenticated()]

    def get_object(self):
        user = self.request.user
        pk = self.kwargs.get('pk')
        try:
            obj = ParcelaPlan.objects.select_related('parcela', 'plan').get(pk=pk)
        except ParcelaPlan.DoesNotExist:
            raise NotFound("Suscripción no encontrada.")
        # permiso módulo
        if not tiene_permiso(user, 'planes', 'ver'):
            raise PermissionDenied("No tienes permiso para ver suscripciones.")
        # admin ok
        if role_name(user) in ['superadmin', 'administrador']:
            return obj
        # owner check
        if getattr(obj.parcela, 'usuario', None) == user:
            return obj
        raise PermissionDenied("No tienes permiso sobre esta suscripción.")

#
# Public Plans
#
@extend_schema(
    tags=['Public'],
    summary='Listar planes públicos (sin autenticación)',
    description=(
        "Devuelve la lista de planes disponibles ordenados por precio. "
        "No requiere autenticación. Útil para mostrar en la página de bienvenida o registro."
    ),
    responses={200: PlanSerializer(many=True)},
    examples=[
        OpenApiExample(
            'Lista pública ejemplo',
            description='Respuesta ejemplo de GET /planes/public/',
            value=[{
                "id": 1,
                "nombre": "Básico",
                "descripcion": "Plan básico",
                "veces_por_dia": 3,
                "horarios_por_defecto": ["07:00","15:00","22:00"],
                "precio": "9.99",
                "created_at": "2025-10-20T00:00:00Z",
                "updated_at": "2025-10-20T00:00:00Z"
            }]
        )
    ]
)
class PublicPlanListView(generics.ListAPIView):
    """
    Endpoint público para listar los planes disponibles.
    No requiere autenticación ni permisos especiales.
    Útil para mostrar en la página de bienvenida o registro.
    """
    queryset = Plan.objects.all().order_by('precio')
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]
