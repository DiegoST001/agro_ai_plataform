from datetime import datetime, timedelta, time
from django.utils import timezone
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework.exceptions import PermissionDenied, NotFound 
from .auth import NodeTokenAuthentication
from .models import Node, NodoSecundario, Parcela
from agro_ai_platform.mongo import get_db, to_utc, now_utc, to_lima
from .serializers import NodeSerializer, NodoSecundarioSerializer
# reemplazado: import directo de helpers de permisos del app nodes (reusa users.permissions)
from .permissions import tiene_permiso, role_name, HasOperationPermission
from .permissions import OwnsNodeOrAdmin  # <- nuevo
from django.db.models import Q
from rest_framework.generics import GenericAPIView
from rest_framework import serializers
from recommendations.rules_engine import upsert_alert

# márgenes por defecto (usados en Swagger y en la vista)
PRE_MARGIN_DEFAULT = 10
POST_MARGIN_DEFAULT = 20

def readings_collection(name):
    # usa get_db() de forma lazy para evitar import-time issues
    db = get_db()
    return db[name]

class NodeIngestSerializer(serializers.Serializer):
    nodo_id = serializers.IntegerField()
    payload = serializers.JSONField()

@extend_schema(
    tags=['Ingesta'],
    summary='Ingesta de datos desde nodo maestro',
    description=(
        "Recibe datos de sensores enviados por el nodo maestro y los almacena en MongoDB.\n\n"
        "Validaciones principales:\n"
        "- Requiere token de nodo (Node <KEY> / X-Node-Token).\n"
        "- Cada nodo secundario debe pertenecer al maestro autenticado.\n"
        "- Se busca el ParcelaPlan más reciente con estado 'activo' o 'programado' y fecha_inicio <= fecha del timestamp.\n"
        "- Si no hay plan válido: se rechaza con reason=no_plan_activo.\n"
        "- Límite diario = veces_por_dia del plan.\n"
        "- Ventanas: horarios_por_defecto (o generación interna). Cada horario acepta una lectura dentro de ±5 minutos.\n"
        "- Errores diferenciados por 'reason'."
    ),
    request={   # <- cambiar a "application/json" para que Swagger muestre el example
        "application/json": {
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
                            "nodo_codigo": {"type": "string", "example": "NODE-01-S1"},
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
            "required": ["timestamp", "lecturas"],
            "example": {
                "codigo_nodo_maestro": "NODE-001",
                "timestamp": "2025-10-01T08:00:00Z",
                "lecturas": [
                    {
                        "nodo_codigo": "NODE-01-S1",
                        "last_seen": "2025-10-01T07:59:50Z",
                        "sensores": [
                            { "sensor": "temperatura", "valor": 22.5, "unidad": "°C" },
                            { "sensor": "humedad", "valor": 65.2, "unidad": "%" }
                        ]
                    }
                ]
            }
        }
    },
    examples=[
        OpenApiExample(
            'Payload mínimo (sin parcela_id)',
            value={
                "codigo_nodo_maestro": "NODE-001",
                "timestamp": "2025-10-01T08:00:00Z",
                "lecturas": [
                    {
                        "nodo_codigo": "NODE-01-S1",
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
class NodeIngestView(GenericAPIView):
    authentication_classes = [NodeTokenAuthentication]
    permission_classes = []
    serializer_class = NodeIngestSerializer

    # márgenes por defecto para ventana de schedule (antes / después)
    PRE_MARGIN_MINUTES = PRE_MARGIN_DEFAULT
    POST_MARGIN_MINUTES = POST_MARGIN_DEFAULT

    def post(self, request):
        payload = request.data.copy()
        ts = payload.get("timestamp")
        try:
            ts_utc = to_utc(ts) if ts else now_utc()
        except Exception:
            # si timestamp inválido, usar now()
            ts_utc = now_utc()
        payload["timestamp"] = ts_utc

        db = get_db()

        token = getattr(request, "auth", None)
        nodo_auth = getattr(request, "node", None)
        if not token or not nodo_auth:
            return Response({'detail': 'No autorizado', 'reason': 'auth_required'}, status=status.HTTP_401_UNAUTHORIZED)

        ts = payload.get("timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                ts = None
        ts = ts or timezone.now()
        tz = timezone.get_current_timezone()
        ts_local = ts.astimezone(tz) if getattr(ts, 'tzinfo', None) else timezone.make_aware(ts, tz)

        # Normalizar a hora local de Lima para validación de ventana
        try:
            ts_local = to_lima(ts_utc)
        except Exception:
            # si falla la conversión, continuar con tz actual
            pass

        node = nodo_auth
        parcela = getattr(node, "parcela", None)
        if not node or not parcela:
            return Response({'detail': 'Nodo o parcela desconocidos', 'reason': 'nodo_parcela_missing'}, status=status.HTTP_400_BAD_REQUEST)

        payload_master_code = (payload or {}).get("codigo_nodo_maestro")
        if payload_master_code and str(payload_master_code).strip() != str(node.codigo).strip():
            return Response(
                {"detail": "codigo_nodo_maestro no coincide con el token proporcionado.", 'reason': 'codigo_maestro_mismatch'},
                status=status.HTTP_403_FORBIDDEN
            )

        lectura_nodes = [(l.get("nodo_codigo") or "").strip() for l in (payload or {}).get("lecturas", []) if l.get("nodo_codigo")]
        if lectura_nodes:
            existentes = set(
                NodoSecundario.objects.filter(codigo__in=lectura_nodes, maestro=node).values_list("codigo", flat=True)
            )
            invalid = [c for c in lectura_nodes if c not in existentes]
            if invalid:
                return Response(
                    {"detail": "Nodos secundarios inválidos o no pertenecen al maestro.", "invalid_nodo_codigos": invalid, 'reason': 'nodos_secundarios_invalidos'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Buscar plan aplicable (activo o programado) cuyo inicio <= fecha
        from plans.models import ParcelaPlan
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

        if not parcela_plan or not getattr(parcela_plan, 'plan', None):
            return Response(
                {"detail": "No hay suscripción/plan vigente para esta fecha.", 'reason': 'no_plan_activo'},
                status=status.HTTP_403_FORBIDDEN
            )

        plan = parcela_plan.plan

        # Validación: hora local (Lima) dentro de rango permitido del plan
        try:
            horarios = plan.get_schedule_for_date(ts_local.date(), tz=tz) or []
            # calcular ventana [start_hour, end_hour) basada en horarios del plan
            horas = [h.hour for h in horarios]
            if horas:
                start_hour = min(horas)
                end_hour = max(horas) + 1  # rango semiabierto
                if not (start_hour <= ts_local.hour < end_hour):
                    return Response(
                        {"error": "timestamp fuera de horario permitido", "reason": "fuera_de_horario"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        except Exception:
            # si get_schedule_for_date falla, continuar y validar más adelante con la ventana ±5 min existente
            pass

        # límite diario = veces_por_dia
        try:
            limite = int(getattr(plan, 'veces_por_dia', 0)) if plan.veces_por_dia else None
        except Exception:
            limite = None

        start_day = timezone.make_aware(datetime.combine(ts_local.date(), time.min), tz)
        end_day = timezone.make_aware(datetime.combine(ts_local.date() + timedelta(days=1), time.min), tz)
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
                "detail": "Límite diario alcanzado según el plan.",
                "limit": limite,
                "current": current_count,
                "reason": "limite_diario"
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # Horarios para hoy
        try:
            schedule = plan.get_schedule_for_date(ts_local.date(), tz=tz) or []
        except Exception:
            schedule = []

        if not schedule:
            return Response({
                "detail": "El plan no define horarios para hoy.",
                "reason": "plan_sin_horarios"
            }, status=status.HTTP_403_FORBIDDEN)

        pre = timedelta(minutes=5)
        post = timedelta(minutes=5)
        matched_slot = None
        for scheduled_dt in schedule:
            if (scheduled_dt - pre) <= ts_local <= (scheduled_dt + post):
                matched_slot = scheduled_dt
                break

        if not matched_slot:
            return Response({
                "detail": "Timestamp fuera de ventanas programadas (±5 min).",
                "timestamp": ts_local.isoformat(),
                "plan_id": plan.id,
                "horarios": [h.isoformat() for h in schedule],
                "reason": "fuera_de_ventana"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Evitar duplicado en slot
        window_start = matched_slot - pre
        window_end = matched_slot + post
        mongo_q_slot = {
            "codigo_nodo_maestro": node.codigo,
            "parcela_id": parcela.id,
            "timestamp": {"$gte": window_start, "$lt": window_end}
        }
        try:
            slot_count = readings_collection("lecturas_sensores").count_documents(mongo_q_slot)
        except Exception:
            slot_count = 0
        if slot_count >= 1:
            return Response({
                "detail": "Ya existe una lectura en esta ventana.",
                "slot_center": matched_slot.isoformat(),
                "reason": "slot_ocupado"
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        mongo_doc = {
            "seed_tag": (payload or {}).get("seed_tag", "demo"),
            "parcela_id": parcela.id,
            "codigo_nodo_maestro": node.codigo,
            "timestamp": ts_local,
            "lecturas": []
        }
        present_codes = set()
        for lectura in (payload or {}).get("lecturas", []):
            codigo = lectura.get("nodo_codigo")
            mongo_doc["lecturas"].append({
                "nodo_codigo": codigo,
                "last_seen": lectura.get("last_seen"),
                "sensores": lectura.get("sensores", []),
            })
            if codigo:
                present_codes.add(codigo)

        readings_collection("lecturas_sensores").insert_one(mongo_doc)

        now = timezone.now()
        node.last_seen = now
        node.estado = payload.get("estado", "activo")
        update_fields = ["last_seen", "estado"]
        for attr in ["bateria", "senal", "lat", "lng"]:
            if attr in payload and payload.get(attr) is not None:
                try:
                    node.__setattr__(attr, payload.get(attr))
                    update_fields.append(attr)
                except Exception:
                    pass
        node.save(update_fields=list(dict.fromkeys(update_fields)))

        if node.bateria is not None and node.bateria < 20:
            upsert_alert(parcela, "Batería baja nodo maestro",
                         f"Nivel batería {node.bateria}%", code=f"node_bateria_{node.id}",
                         severity='high', entity_type='node', entity_ref=str(node.id),
                         meta={'bateria': node.bateria}, source='rules.node')
        if node.senal is not None and node.senal < -90:
            upsert_alert(parcela, "Señal débil nodo maestro",
                         f"Señal {node.senal}dBm", code=f"node_senal_{node.id}",
                         severity='medium', entity_type='node', entity_ref=str(node.id),
                         meta={'senal': node.senal}, source='rules.node')

        for lectura in payload.get("lecturas", []):
            codigo_sec = lectura.get("nodo_codigo")
            if not codigo_sec:
                continue
            try:
                nodo_sec = NodoSecundario.objects.get(codigo=codigo_sec, maestro=node)
                changed = []
                ls = lectura.get("last_seen")
                parsed_ls = None
                if isinstance(ls, str):
                    try:
                        parsed_ls = datetime.fromisoformat(ls.replace("Z", "+00:00"))
                        if getattr(parsed_ls, 'tzinfo', None) is None:
                            parsed_ls = timezone.make_aware(parsed_ls, tz)
                    except Exception:
                        parsed_ls = None
                nodo_sec.last_seen = parsed_ls or now
                changed.append("last_seen")
                estado_val = lectura.get("estado", "activo")
                if estado_val:
                    nodo_sec.estado = estado_val
                    changed.append("estado")
                if "bateria" in lectura and lectura.get("bateria") is not None:
                    try:
                        nodo_sec.bateria = int(lectura.get("bateria"))
                        changed.append("bateria")
                    except Exception:
                        pass
                if changed:
                    nodo_sec.save(update_fields=list(dict.fromkeys(changed)))
            except NodoSecundario.DoesNotExist:
                continue

        qs_absent = NodoSecundario.objects.filter(maestro=node)
        if present_codes:
            qs_absent = qs_absent.exclude(codigo__in=list(present_codes))
        qs_absent.update(estado="inactivo")

        return Response({"detail": "OK", "reason": "ingesta_aceptada"}, status=status.HTTP_200_OK)

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
    description='Actualiza un nodo maestro. Requiere nudos.actualizar. Agricultor solo si es dueño de la parcela.',
    request=NodeSerializer,  # PUT (completo)
    responses=NodeSerializer,
    examples=[
        OpenApiExample(
            'PUT completo (maestro)',
            value={
                "lat": -12.05,
                "lng": -77.05,
                "estado": "activo",
                "bateria": 80,
                "senal": -72,
                "last_seen": "2025-12-10T14:10:00Z"
            },
            request_only=True
        ),
        OpenApiExample(
            'PATCH parcial (maestro)',
            value={
                "estado": "inactivo",
                "bateria": 15
            },
            request_only=True
        ),
    ]
)
class NodeUpdateView(generics.UpdateAPIView):
    serializer_class = NodeSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'actualizar'), OwnsNodeOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'actualizar'):
            raise PermissionDenied(detail="No tienes permiso para actualizar nodos.")
        if role_name(user) == 'agricultor':
            return Node.objects.filter(parcela__usuario=user)
        return Node.objects.all()

    @extend_schema(
        request=NodeSerializer,  # PATCH (parcial)
        responses=NodeSerializer,
        examples=[OpenApiExample('PATCH ejemplo', value={"estado": "activo", "bateria": 95}, request_only=True)]
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

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
    description='Actualiza un nodo secundario. Requiere nudos.actualizar. Agricultor solo si es dueño de la parcela del maestro.',
    request=NodoSecundarioSerializer,  # PUT
    responses=NodoSecundarioSerializer,
    examples=[
        OpenApiExample(
            'PUT completo (secundario)',
            value={
                "estado": "activo",
                "bateria": 90,
                "last_seen": "2025-12-10T14:20:00Z"
            },
            request_only=True
        ),
        OpenApiExample(
            'PATCH parcial (secundario)',
            value={"estado": "inactivo"},
            request_only=True
        ),
    ]
)
class NodoSecundarioUpdateView(generics.UpdateAPIView):
    serializer_class = NodoSecundarioSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'actualizar'), OwnsNodeOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'actualizar'):
            raise PermissionDenied(detail="No tienes permiso para actualizar nodos secundarios.")
        if role_name(user) == 'agricultor':
            return NodoSecundario.objects.filter(maestro__parcela__usuario=user)
        return NodoSecundario.objects.all()

    @extend_schema(
        request=NodoSecundarioSerializer,  # PATCH
        responses=NodoSecundarioSerializer,
        examples=[OpenApiExample('PATCH ejemplo', value={"bateria": 50}, request_only=True)]
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)