from datetime import datetime, timedelta, time
from django.utils import timezone
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework.exceptions import PermissionDenied, NotFound 
from .auth import NodeTokenAuthentication
from .models import Node, NodoSecundario, Parcela
from agro_ai_platform.mongo import get_db
from .serializers import NodeSerializer, NodoSecundarioSerializer
# reemplazado: import directo de helpers de permisos del app nodes (reusa users.permissions)
from .permissions import tiene_permiso, role_name, HasOperationPermission
from .permissions import OwnsNodeOrAdmin  # <- nuevo
from django.db.models import Q

# márgenes por defecto (usados en Swagger y en la vista)
PRE_MARGIN_DEFAULT = 10
POST_MARGIN_DEFAULT = 20

def readings_collection(name):
    # usa get_db() de forma lazy para evitar import-time issues
    db = get_db()
    return db[name]

@extend_schema(
    tags=['Ingesta'],
    summary='Ingesta de datos desde nodo maestro',
    description=(
        "Recibe datos de sensores enviados por el nodo maestro y los almacena en MongoDB (solo lecturas y sensores). "
        "Autenticación: token de nodo (NodeTokenAuthentication) — request.node y request.auth deben estar presentes.\n\n"
        "Comportamiento y validaciones:\n"
        "- El endpoint valida el plan activo de la parcela asociada al nodo (ParcelaPlan -> Plan).\n"
        "- Si existe un plan activo se aplican:\n"
        "  * Límite máximo de ingestiones por día (plan.limite_lecturas_dia o veces_por_dia).\n"
        "  * Validación de ventanas horarias programadas (plan.get_schedule_for_date) con ventana "
        f"(−{PRE_MARGIN_DEFAULT}min, +{POST_MARGIN_DEFAULT}min) por horario.\n"
        "- Si la ingestión excede el límite diario o está fuera de todas las ventanas válidas, retorna 429 o 400.\n\n"
        "Importante:\n"
        "- NO envíes 'parcela_id'; se infiere del nodo autenticado. "
        "Opcionalmente puedes enviar 'codigo_nodo_maestro', pero se usará el del token.\n\n"
        "Datos almacenados en MongoDB:\n"
        "- Documento: seed_tag, parcela_id (derivado), codigo_nodo_maestro (derivado), timestamp y lecturas[].\n"
        "- Cada lectura: nodo_codigo, last_seen, sensores[]. NO se guarda 'bateria' en MongoDB.\n"
    ),
    request={
        "type": "object",
        "properties": {
            "codigo_nodo_maestro": {"type": "string", "example": "NODE-001", "description": "Opcional; se usa el del token si no se envía."},
            "timestamp": {"type": "string", "format": "date-time", "example": "2025-09-24T18:30:00Z"},
            "last_seen": {"type": "string", "format": "date-time", "example": "2025-10-01T07:59:50Z"},
            "estado": {"type": "string", "example": "activo"},
            "lat": {"type": "string", "example": "-13.53"},
            "lng": {"type": "string", "example": "-70.65"},
            "senal": {"type": "string", "example": "-70dBm"},
            "lecturas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "nodo_codigo": {"type": "string", "example": "NODE-01"},
                        "bateria": {"type": "integer", "example": 95, "description": "Aceptada en payload pero NO persistida en MongoDB; se guarda en Postgres."},
                        "last_seen": {"type": "string", "format": "date-time", "example": "2025-10-01T07:59:50Z"},
                        "sensores": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "sensor": {"type": "string", "example": "temperatura"},
                                    "valor": {"type": "number", "example": 22.5},
                                    "unidad": {"type": "string", "example": "°C"}
                                }
                            }
                        }
                    },
                    "required": ["nodo_codigo", "sensores"]
                }
            }
        },
        "required": ["timestamp", "lecturas"]
    },
    examples=[
        OpenApiExample(
            'Payload mínimo (sin parcela_id)',
            value={
                "codigo_nodo_maestro": "NODE-001",
                "timestamp": "2025-10-01T08:00:00Z",
                "lecturas": [
                    {
                        "nodo_codigo": "NODE-01",
                        "last_seen": "2025-10-01T07:59:50Z",
                        "sensores": [
                            { "sensor": "temperatura", "valor": 22.5, "unidad": "°C" },
                            { "sensor": "humedad", "valor": 65.2, "unidad": "%" }
                        ]
                    }
                ]
            },
            request_only=True
        )
    ]
)
class NodeIngestView(views.APIView):
    authentication_classes = [NodeTokenAuthentication]
    permission_classes = [permissions.AllowAny]

    # márgenes por defecto para ventana de schedule (antes / después)
    PRE_MARGIN_MINUTES = PRE_MARGIN_DEFAULT
    POST_MARGIN_MINUTES = POST_MARGIN_DEFAULT

    def post(self, request):
        # 0) autenticación por token de nodo (NodeTokenAuthentication debe setear request.node y request.auth)
        token = getattr(request, "auth", None)
        nodo_auth = getattr(request, "node", None)
        if not token or not nodo_auth:
            return Response({'detail': 'No autorizado'}, status=status.HTTP_401_UNAUTHORIZED)

        payload = request.data or {}
        # normalizar timestamp (acepta ISO string o None)
        ts = payload.get("timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                ts = None
        ts = ts or timezone.now()

        # NORMALIZAR zona y ts_local aquí para usar en la búsqueda de planes
        tz = timezone.get_current_timezone()
        ts_local = ts.astimezone(tz) if getattr(ts, 'tzinfo', None) else timezone.make_aware(ts, tz)

        # el nodo viene del token; opcionalmente cae el código en payload
        node = nodo_auth
        parcela = getattr(node, "parcela", None)
        if not node or not parcela:
            return Response({'detail': 'Nodo o parcela desconocidos'}, status=status.HTTP_400_BAD_REQUEST)

        # seguridad adicional: si el payload incluye codigo_nodo_maestro debe coincidir con el token
        payload_master_code = (payload or {}).get("codigo_nodo_maestro")
        if payload_master_code:
            if str(payload_master_code).strip() != str(node.codigo).strip():
                return Response(
                    {"detail": "codigo_nodo_maestro no coincide con el token proporcionado."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # seguridad adicional: validar que cada 'nodo_codigo' en 'lecturas' exista y pertenezca al maestro autenticado
        lectura_nodes = [(l.get("nodo_codigo") or "").strip() for l in (payload or {}).get("lecturas", []) if l.get("nodo_codigo")]
        invalid_codes = []
        if lectura_nodes:
            # buscar existentes que pertenezcan al maestro
            existentes = set(
                NodoSecundario.objects.filter(codigo__in=lectura_nodes, maestro=node).values_list("codigo", flat=True)
            )
            for code in lectura_nodes:
                if code not in existentes:
                    invalid_codes.append(code)
            if invalid_codes:
                return Response(
                    {
                        "detail": "Algunos nodos secundarios no pertenecen al nodo maestro autenticado o no existen.",
                        "invalid_nodo_codigos": invalid_codes
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

        # consultar ParcelaPlan que cubra la fecha del timestamp (activo o programado)
        try:
            from plans.models import ParcelaPlan
        except Exception:
            ParcelaPlan = None

        parcela_plan = None
        if ParcelaPlan:
            parcela_plan = (
                ParcelaPlan.objects
                .select_related('plan')
                .filter(
                    parcela=parcela,
                    estado__in=['activo', 'programado'],
                    fecha_inicio__lte=ts_local.date()
                )
                .filter(
                    Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=ts_local.date())
                )
                .order_by('-fecha_inicio')
                .first()
            )

        # Si existe un plan vigente para la fecha, aplicamos validaciones (límite diario + ventanas)
        if parcela_plan and parcela_plan.plan:
            plan = parcela_plan.plan
            # determinar límite diario (veces_por_dia o limite_lecturas_dia)
            limite = getattr(plan, 'limite_lecturas_dia', None) or getattr(plan, 'veces_por_dia', None)
            try:
                limite = int(limite) if limite is not None else None
            except Exception:
                limite = None

            # límites del día (00:00 y 24:00) en la zona horaria del servidor
            start_naive = datetime.combine(ts_local.date(), time.min)
            end_naive = datetime.combine(ts_local.date() + timedelta(days=1), time.min)
            start_day = timezone.make_aware(start_naive, tz)
            end_day = timezone.make_aware(end_naive, tz)

            mongo_q = {
                "codigo_nodo_maestro": node.codigo,
                "parcela_id": parcela.id,
                "timestamp": {"$gte": start_day, "$lt": end_day}
            }
            try:
                current_count = readings_collection("lecturas_sensores").count_documents(mongo_q)
            except Exception:
                current_count = 0

            if limite is not None and current_count >= limite:
                return Response({
                    "detail": "Límite de lecturas por día alcanzado para este nodo/parcela según el plan.",
                    "limit": limite,
                    "current": current_count
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            # obtener horarios para la fecha: preferir plan.get_schedule_for_date, si no existe usar horarios_por_defecto
            schedule = []
            try:
                if hasattr(plan, 'get_schedule_for_date'):
                    schedule = plan.get_schedule_for_date(ts_local.date(), tz=tz) or []
                else:
                    # generar datetimes a partir de plan.horarios_por_defecto que se espera sea lista de "HH:MM"
                    horarios = getattr(plan, 'horarios_por_defecto', []) or []
                    for h in horarios:
                        try:
                            hh, mm = [int(x) for x in h.split(':')]
                            dt_naive = datetime.combine(ts_local.date(), time(hh, mm))
                            schedule.append(timezone.make_aware(dt_naive, tz))
                        except Exception:
                            continue
            except Exception:
                schedule = []

            if schedule:
                pre = timedelta(minutes=self.PRE_MARGIN_MINUTES)
                post = timedelta(minutes=self.POST_MARGIN_MINUTES)
                in_window = False
                for scheduled_dt in schedule:
                    window_start = scheduled_dt - pre
                    window_end = scheduled_dt + post
                    if window_start <= ts_local <= window_end:
                        in_window = True
                        break
                if not in_window:
                    return Response({
                        "detail": "Timestamp fuera de ventanas programadas para hoy según el plan activo.",
                        "timestamp": ts_local.isoformat(),
                        "plan_id": plan.id,
                        "plan_nombre": getattr(plan, 'nombre', None),
                        "windows": [
                            {"start": (sd - pre).isoformat(), "center": sd.isoformat(), "end": (sd + post).isoformat()}
                            for sd in schedule
                        ],
                        "nota": "Si deseas programar el siguiente plan, revisa las fechas de ParcelaPlan."
                    }, status=status.HTTP_400_BAD_REQUEST)

        # construir documento mongo (SIN 'bateria') y sin leer parcela_id del payload
        mongo_doc = {
            "seed_tag": (request.data or {}).get("seed_tag", "demo"),
            "parcela_id": parcela.id,                 # derivado del nodo
            "codigo_nodo_maestro": node.codigo,       # derivado del nodo
            "timestamp": ts,
            "lecturas": []
        }
        present_codes = set()
        for lectura in (request.data or {}).get("lecturas", []):
            codigo = lectura.get("nodo_codigo")
            lectura_doc = {
                "nodo_codigo": codigo,
                "last_seen": lectura.get("last_seen"),
                "sensores": lectura.get("sensores", []),
            }
            mongo_doc["lecturas"].append(lectura_doc)
            if codigo:
                present_codes.add(codigo)

        readings_collection("lecturas_sensores").insert_one(mongo_doc)
        # actualizar maestro en Postgres (se mantiene la lógica anterior)
        now = timezone.now()
        node.last_seen = now
        node.estado = payload.get("estado", "activo")
        update_fields = ["last_seen", "estado"]

        if "bateria" in payload and payload.get("bateria") is not None:
            try:
                node.bateria = int(payload.get("bateria"))
                update_fields.append("bateria")
            except (ValueError, TypeError):
                pass

        if "senal" in payload and payload.get("senal") is not None:
            try:
                node.senal = int(payload.get("senal"))
                update_fields.append("senal")
            except (ValueError, TypeError):
                pass

        if "lat" in payload and payload.get("lat") is not None:
            node.lat = payload.get("lat")
            update_fields.append("lat")
        if "lng" in payload and payload.get("lng") is not None:
            node.lng = payload.get("lng")
            update_fields.append("lng")

        node.save(update_fields=list(dict.fromkeys(update_fields)))

        # actualizar nodos secundarios presentes y marcar como inactivos los ausentes
        for lectura in payload.get("lecturas", []):
            codigo_sec = lectura.get("nodo_codigo")
            if not codigo_sec:
                continue
            try:
                nodo_sec = NodoSecundario.objects.get(codigo=codigo_sec)
                changed_fields = []
                if lectura.get("last_seen") is not None:
                    try:
                        nodo_sec.last_seen = lectura.get("last_seen")
                        changed_fields.append("last_seen")
                    except Exception:
                        pass
                estado_val = lectura.get("estado", "activo")
                if estado_val is not None:
                    nodo_sec.estado = estado_val
                    changed_fields.append("estado")
                # batería (acepta 0) -> se guarda en Postgres
                if "bateria" in lectura and lectura.get("bateria") is not None:
                    try:
                        nodo_sec.bateria = int(lectura.get("bateria"))
                        changed_fields.append("bateria")
                    except (ValueError, TypeError):
                        pass
                if changed_fields:
                    nodo_sec.save(update_fields=list(dict.fromkeys(changed_fields)))
            except NodoSecundario.DoesNotExist:
                continue

        if node is not None:
            qs_absent = NodoSecundario.objects.filter(maestro=node)
            if present_codes:
                qs_absent = qs_absent.exclude(codigo__in=list(present_codes))
            qs_absent.update(estado="inactivo")

        return Response({"detail": "OK"}, status=status.HTTP_200_OK)

@extend_schema(
    tags=['Nodos'],
    summary='Listar nodos maestros de una parcela',
    description='Devuelve todos los nodos maestros asociados a una parcela específica.',
)
class NodoMasterListView(generics.ListAPIView):
    serializer_class = NodeSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'ver')]

    def get_queryset(self):
        user = self.request.user
        parcela_id = self.kwargs.get('parcela_id')

        # verificar existencia de parcela -> 404 si no existe
        try:
            parcela = Parcela.objects.get(id=parcela_id)
        except Parcela.DoesNotExist:
            raise NotFound(detail="Parcela no existe.")

        # permiso de módulo
        if not tiene_permiso(user, 'nodos', 'ver'):
            raise PermissionDenied(detail="No tienes permiso para ver nodos.")

        # admin puede ver todo; agricultor solo sus parcelas
        if role_name(user) in ['superadmin', 'administrador']:
            return Node.objects.filter(parcela_id=parcela_id)
        if parcela.usuario == user:
            return Node.objects.filter(parcela_id=parcela_id)

        raise PermissionDenied(detail="No tienes permiso para ver los nodos de esta parcela.")

@extend_schema(
    tags=['Nodos'],
    summary='Listar nodos secundarios de un nodo maestro',
    description='Devuelve todos los nodos secundarios asociados a un nodo maestro específico.',
)
class NodoSecundarioListView(generics.ListAPIView):
    serializer_class = NodoSecundarioSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'ver')]

    def get_queryset(self):
        user = self.request.user
        nodo_master_id = self.kwargs.get('nodo_master_id')

        # comprobar existencia del maestro -> 404
        try:
            nodo_master = Node.objects.select_related('parcela').get(id=nodo_master_id)
        except Node.DoesNotExist:
            raise NotFound(detail="Nodo maestro no existe.")

        # permiso de módulo
        if not tiene_permiso(user, 'nodos', 'ver'):
            raise PermissionDenied(detail="No tienes permiso para ver nodos.")

        # admin puede ver siempre
        if role_name(user) in ['superadmin', 'administrador']:
            return NodoSecundario.objects.filter(maestro_id=nodo_master_id)

        # propietario de la parcela puede ver
        if getattr(nodo_master.parcela, 'usuario', None) == user:
            return NodoSecundario.objects.filter(maestro_id=nodo_master_id)

        raise PermissionDenied(detail="No tienes permiso para ver los nodos secundarios de este nodo maestro.")

@extend_schema(
    tags=['Nodos'],
    summary='Crear nodo maestro para una parcela',
    description='Permite crear un nodo maestro y asociarlo a una parcela. El código se genera automáticamente.',
    request=NodeSerializer,
    responses=NodeSerializer,
    examples=[
        OpenApiExample(
            'Ejemplo de creación de nodo maestro',
            value={
                "lat": -13.53,
                "lng": -70.65,
                "estado": "activo",
                "bateria": 95,
                "senal": -70,
                "last_seen": "2025-10-12T10:28:56.159Z"
            },
            request_only=True
        )
    ]
)
class NodeCreateView(generics.CreateAPIView):
    serializer_class = NodeSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'crear')]

    def perform_create(self, serializer):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'crear'):
            raise PermissionDenied("No tienes permiso para crear nodos.")
        parcela_id = self.kwargs.get('parcela_id')
        # verificar existencia de parcela -> 404
        try:
            parcela = Parcela.objects.get(id=parcela_id)
        except Parcela.DoesNotExist:
            raise NotFound(detail="Parcela no existe.")
        if role_name(user) == 'agricultor' and parcela.usuario != user:
            raise PermissionDenied("No puedes crear nodos en parcelas que no son tuyas.")
        serializer.save(parcela_id=parcela_id)

@extend_schema(
    tags=['Nodos'],
    summary='Actualizar nodo maestro',
    description='Permite actualizar los datos de un nodo maestro existente.',
    request=NodeSerializer,
    responses=NodeSerializer,
)
class NodeUpdateView(generics.UpdateAPIView):
    serializer_class = NodeSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'actualizar'), OwnsNodeOrAdmin()]  # <- cambio

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'actualizar'):
            raise PermissionDenied(detail="No tienes permiso para actualizar nodos.")
        if role_name(user) == 'agricultor':
            return Node.objects.filter(parcela__usuario=user)
        return Node.objects.all()

@extend_schema(
    tags=['Nodos'],
    summary='Crear nodo secundario para un nodo maestro',
    description='Permite crear un nodo secundario asociado a un nodo maestro específico.',
    request=NodoSecundarioSerializer,
    responses=NodoSecundarioSerializer,
    examples=[
        OpenApiExample(
            'Ejemplo de creación de nodo secundario',
            value={
                "estado": "activo",
                "bateria": 90,
                "last_seen": "2025-10-12T10:30:00.000Z"
            },
            request_only=True
        )
    ]
)
class NodoSecundarioCreateView(generics.CreateAPIView):
    serializer_class = NodoSecundarioSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'crear')]

    def perform_create(self, serializer):
        user = self.request.user
        maestro_id = self.kwargs.get('nodo_master_id')
        try:
            nodo_master = Node.objects.select_related('parcela').get(id=maestro_id)
        except Node.DoesNotExist:
            raise NotFound(detail="Nodo maestro no existe.")
        # permiso de módulo
        if not tiene_permiso(user, 'nodos', 'crear'):
            raise PermissionDenied(detail="No tienes permiso para crear nodos secundarios.")
        if role_name(user) in ['superadmin', 'administrador'] or getattr(nodo_master.parcela, 'usuario', None) == user:
            serializer.save(maestro_id=maestro_id)
            return
        raise PermissionDenied(detail="No tienes permiso para crear nodos secundarios en este nodo maestro.")

@extend_schema(
    tags=['Nodos'],
    summary='Listar todos los nodos maestros',
    description='Devuelve todos los nodos maestros registrados en el sistema.',
)
class NodeListView(generics.ListAPIView):
    serializer_class = NodeSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'ver')]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'ver'):
            raise PermissionDenied(detail="No tienes permiso para ver nodos.")
        if role_name(user) == 'agricultor':
            parcelas = Parcela.objects.filter(usuario=user)
            return Node.objects.filter(parcela__in=parcelas)
        return Node.objects.all()

@extend_schema(
    tags=['Nodos'],
    summary='Detalle de nodo maestro',
    description='Devuelve los datos completos de un nodo maestro, incluyendo sus nodos secundarios asociados.',
)
class NodeDetailView(generics.RetrieveAPIView):
    serializer_class = NodeSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'ver'), OwnsNodeOrAdmin()]  # <- cambio
    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'ver'):
            raise PermissionDenied(detail="No tienes permiso para ver nodos.")
        if role_name(user) in ['superadmin', 'administrador']:
            return Node.objects.all()
        return Node.objects.filter(parcela__usuario=user)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['include_secundarios'] = True
        return ctx

@extend_schema(
    tags=['Nodos'],
    summary='Eliminar nodo maestro',
    description='Permite eliminar un nodo maestro existente.',
)
class NodeDeleteView(generics.DestroyAPIView):
    serializer_class = NodeSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'eliminar'), OwnsNodeOrAdmin()]  # <- cambio

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'eliminar'):
            raise PermissionDenied(detail="No tienes permiso para eliminar nodos.")
        if role_name(user) == 'agricultor':
            return Node.objects.filter(parcela__usuario=user)
        return Node.objects.all()

@extend_schema(
    tags=['Nodos'],
    summary='Eliminar nodo secundario',
    description='Permite eliminar un nodo secundario existente.',
)
class NodoSecundarioDeleteView(generics.DestroyAPIView):
    serializer_class = NodoSecundarioSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'eliminar'), OwnsNodeOrAdmin()]  # <- cambio

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'eliminar'):
            raise PermissionDenied(detail="No tienes permiso para eliminar nodos secundarios.")
        if role_name(user) == 'agricultor':
            return NodoSecundario.objects.filter(maestro__parcela__usuario=user)
        return NodoSecundario.objects.all()

@extend_schema(
    tags=['Nodos'],
    summary='Listar todos los nodos secundarios',
    description='Devuelve todos los nodos secundarios registrados en el sistema.',
)
class NodoSecundarioListAllView(generics.ListAPIView):
    serializer_class = NodoSecundarioSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'ver')]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'ver'):
            raise PermissionDenied(detail="No tienes permiso para ver nodos secundarios.")
        if role_name(user) == 'agricultor':
            return NodoSecundario.objects.filter(maestro__parcela__usuario=user)
        return NodoSecundario.objects.all()

@extend_schema(
    tags=['Nodos'],
    summary='Detalle de nodo secundario',
    description='Devuelve los datos completos de un nodo secundario.',
)
class NodoSecundarioDetailView(generics.RetrieveAPIView):
    serializer_class = NodoSecundarioSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'ver'), OwnsNodeOrAdmin()]  # <- cambio

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'ver'):
            raise PermissionDenied(detail="No tienes permiso para ver nodos secundarios.")
        if role_name(user) in ['superadmin', 'administrador']:
            return NodoSecundario.objects.all()
        return NodoSecundario.objects.filter(maestro__parcela__usuario=user)

@extend_schema(
    tags=['Nodos'],
    summary='Actualizar nodo secundario',
    description='Permite actualizar los datos de un nodo secundario existente.',
    request=NodoSecundarioSerializer,
    responses=NodoSecundarioSerializer,
)
class NodoSecundarioUpdateView(generics.UpdateAPIView):
    serializer_class = NodoSecundarioSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'actualizar'), OwnsNodeOrAdmin()]  # <- cambio

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'actualizar'):
            raise PermissionDenied(detail="No tienes permiso para actualizar nodos secundarios.")
        if role_name(user) == 'agricultor':
            return NodoSecundario.objects.filter(maestro__parcela__usuario=user)
        return NodoSecundario.objects.all()