from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiExample
from .services import (
    compute_kpis_for_user,
    aggregate_timeseries,
    fetch_history,
    compute_daily_kpis_parcela,
    compute_daily_kpis_for_user,
)
from .serializers import KPISerializer, TimeSeriesResponseSerializer, DailyParcelKPISerializer, DailyUserKPISerializer
from users.permissions import tiene_permiso, role_name
from django.utils.dateparse import parse_datetime
from agro_ai_platform.mongo import get_db, LIMA_TZ
from django.utils import timezone
from django.db.models.functions import TruncHour, TruncDay
from django.db.models import Count
from .models import AuditLog
from .serializers import AuditSeriesResponseSerializer, AuditLogSerializer
# fallbacks para utilidades opcionales
try:
    from .services import summarize_timeseries, to_utc
except Exception:
    def summarize_timeseries(meta, points):
        return None
    from django.utils import timezone as _tz
    def to_utc(dt_str: str):
        if not dt_str:
            return None
        try:
            dt = parse_datetime(dt_str)
            if dt is None:
                return None
            if dt.tzinfo is None:
                # asumir America/Lima si viene naive
                return dt.replace(tzinfo=LIMA_TZ).astimezone(_tz.utc)
            return dt.astimezone(_tz.utc)
        except Exception:
            return None

# límites ambientales (puedes moverlos a settings/.env si lo deseas)
ENV_LIMITS = {
    "temperatura": {"min": 18, "max": 30, "unidad": "°C", "label": "Temperatura"},
    "humedad_suelo": {"min": 45, "max": 70, "unidad": "%", "label": "Humedad del Suelo"},
    "humedad_aire": {"min": 60, "max": 90, "unidad": "%", "label": "Humedad del Aire"},
}

def _estado_parametro(valor, limits):
    if valor is None:
        return "sin_datos"
    mn, mx = limits["min"], limits["max"]
    if mn <= valor <= mx:
        return "normal"
    # advertencia si está dentro de ±10% del umbral
    pad_min = mn * 0.9
    pad_max = mx * 1.1
    if pad_min <= valor <= pad_max:
        return "advertencia"
    return "peligro"

def _latest_secondary_nodes_for_parcela(db, parcela_id: int):
    # Devuelve lecturas más recientes por nodo secundario y sensor
    coll_name_candidates = ['lecturas_sensores', 'sensor_readings', 'readings']
    coll = None
    for n in coll_name_candidates:
        if n in db.list_collection_names():
            coll = db[n]
            break
    if coll is None:
        return []

    pipeline = [
        {"$match": {"parcela_id": parcela_id}},
        {"$sort": {"timestamp": -1}},
        {"$unwind": "$lecturas"},
        {"$unwind": "$lecturas.sensores"},
        {
            "$project": {
                "nodo": "$lecturas.nodo_codigo",
                "sensor": "$lecturas.sensores.sensor",
                "value": "$lecturas.sensores.valor",
                "last_seen": "$lecturas.last_seen",
                "timestamp": {
                    "$cond": [
                        {"$eq": [{"$type": "$timestamp"}, "date"]},
                        "$timestamp",
                        {"$dateFromString": {"dateString": "$timestamp"}}
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": {"nodo": "$nodo", "sensor": "$sensor"},
                "last_value": {"$first": "$value"},
                "last_seen": {"$first": "$last_seen"},
                "last_ts": {"$first": "$timestamp"}
            }
        },
    ]
    return list(coll.aggregate(pipeline, allowDiskUse=True))

class KPIsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if not tiene_permiso(user, 'parcelas', 'ver'):
            raise PermissionDenied(detail="No tiene permiso para ver KPIs (se requiere parcelas.ver).")

        kpi_type = (request.query_params.get('type') or 'summary').lower()
        if kpi_type == 'daily':
            parcela_id = request.query_params.get('parcela')
            if parcela_id:
                pid = int(parcela_id)
                return Response(compute_daily_kpis_parcela(pid), status=status.HTTP_200_OK)
            return Response(compute_daily_kpis_for_user(user), status=status.HTTP_200_OK)
        return Response(compute_kpis_for_user(user), status=status.HTTP_200_OK)

class TimeSeriesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['brain'],
        summary='Serie temporal para parámetro de parcela',
        description=(
            "Devuelve puntos agregados (avg) para un parámetro de una parcela.\n\n"
            "Query params:\n"
            "- parcela (required)\n"
            "- parametro (required)\n"
            "- period (optional): minute|hour|day|week|month|year\n"
            "- interval (optional): entero (binSize) o 'auto'\n"
            "- start, end (ISO opcionales). Si son naive, se asume America/Lima.\n\n"
            "Combinaciones y ejemplos listos para probar:\n"
            "1) Por hora (últimas 24h):\n"
            "   /api/brain/series/?parcela=2&parametro=temperatura&period=hour&interval=1\n"
            "   Día específico:\n"
            "   /api/brain/series/?parcela=2&parametro=temperatura&period=hour&interval=1&start=2025-11-10&end=2025-11-11\n"
            "2) Por día (promedio diario):\n"
            "   /api/brain/series/?parcela=2&parametro=temperatura&period=day&interval=1\n"
            "   Rango de días:\n"
            "   /api/brain/series/?parcela=2&parametro=temperatura&period=day&interval=1&start=2025-11-01&end=2025-11-20\n"
            "3) Por semana (ISO-8601 lunes–domingo):\n"
            "   /api/brain/series/?parcela=2&parametro=temperatura&period=week&interval=1\n"
            "   Rango:\n"
            "   /api/brain/series/?parcela=2&parametro=temperatura&period=week&interval=1&start=2025-10-01&end=2025-12-01\n"
            "4) Por mes (calendario Lima):\n"
            "   /api/brain/series/?parcela=2&parametro=temperatura&period=month&interval=1\n"
            "   Rango:\n"
            "   /api/brain/series/?parcela=2&parametro=temperatura&period=month&interval=1&start=2025-01-01&end=2025-12-31\n"
            "5) Por año (promedio anual):\n"
            "   /api/brain/series/?parcela=2&parametro=temperatura&period=year&interval=1\n"
            "   Rango:\n"
            "   /api/brain/series/?parcela=2&parametro=temperatura&period=year&interval=1&start=2024-01-01&end=2026-01-01\n\n"
            "Importante:\n"
            "- period soporta: minute, hour, day, week, month, year.\n"
            "- interval = número (binSize). Ejemplo: period=day&interval=7 → buckets de 7 días.\n"
            "Parámetro opcional para series por nodo:\n"
            "- per_node=true → devuelve una serie por cada nodo secundario (estructura con 'series' en vez de 'points').\n\n"
            "Ejemplos per_node:\n"
            "/api/brain/series/?parcela=2&parametro=temperatura&period=day&interval=hour&per_node=true\n"
            "/api/brain/series/?parcela=2&parametro=temperatura&period=week&interval=1&per_node=true\n"
        ),
        parameters=[
            OpenApiParameter(name='parcela', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter(name='parametro', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter(name='period', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False,
                             description="minute|hour|day|week|month|year"),
            OpenApiParameter(name='interval', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False,
                             description="Entero para binSize (p. ej. 1, 7) o 'auto'"),
            OpenApiParameter(name='start', type=OpenApiTypes.DATETIME, location=OpenApiParameter.QUERY, required=False,
                             description="Inicio (ISO8601). Si es naive, se asume America/Lima."),
            OpenApiParameter(name='end', type=OpenApiTypes.DATETIME, location=OpenApiParameter.QUERY, required=False,
                             description="Fin (ISO8601). Si es naive, se asume America/Lima."),
            OpenApiParameter(name='per_node', type=OpenApiTypes.BOOL, location=OpenApiParameter.QUERY, required=False,
                             description="Si true, devuelve series separadas por nodo (series[].points) en lugar de promedio único."),
        ],
        responses={200: TimeSeriesResponseSerializer()},
        examples=[
            OpenApiExample('Por hora (últimas 24h)', value={"/api/brain/series/?parcela=2&parametro=temperatura&period=hour&interval=1"}, request_only=True),
            OpenApiExample('Día específico por hora', value={"/api/brain/series/?parcela=2&parametro=temperatura&period=hour&interval=1&start=2025-11-10&end=2025-11-11"}, request_only=True),
            OpenApiExample('Por día', value={"/api/brain/series/?parcela=2&parametro=temperatura&period=day&interval=1"}, request_only=True),
            OpenApiExample('Rango por día', value={"/api/brain/series/?parcela=2&parametro=temperatura&period=day&interval=1&start=2025-11-01&end=2025-11-20"}, request_only=True),
            OpenApiExample('Por semana', value={"/api/brain/series/?parcela=2&parametro=temperatura&period=week&interval=1"}, request_only=True),
            OpenApiExample('Rango por semana', value={"/api/brain/series/?parcela=2&parametro=temperatura&period=week&interval=1&start=2025-10-01&end=2025-12-01"}, request_only=True),
            OpenApiExample('Por mes', value={"/api/brain/series/?parcela=2&parametro=temperatura&period=month&interval=1"}, request_only=True),
            OpenApiExample('Rango por mes', value={"/api/brain/series/?parcela=2&parametro=temperatura&period=month&interval=1&start=2025-01-01&end=2025-12-31"}, request_only=True),
            OpenApiExample('Por año', value={"/api/brain/series/?parcela=2&parametro=temperatura&period=year&interval=1"}, request_only=True),
            OpenApiExample('Rango por año', value={"/api/brain/series/?parcela=2&parametro=temperatura&period=year&interval=1&start=2024-01-01&end=2026-01-01"}, request_only=True),
            OpenApiExample('Buckets de 7 días', value={"/api/brain/series/?parcela=2&parametro=temperatura&period=day&interval=7"}, request_only=True),
        ]
    )
    def get(self, request):
        user = request.user
        if not tiene_permiso(user, 'parcelas', 'ver'):
            raise PermissionDenied(detail="No tiene permiso para ver series (se requiere parcelas.ver).")

        parcela = request.query_params.get('parcela')
        parametro = request.query_params.get('parametro')
        period = request.query_params.get('period', 'day')
        interval = request.query_params.get('interval')
        per_node_raw = request.query_params.get('per_node')
        per_node = str(per_node_raw).lower() in ('1', 'true', 'yes') if per_node_raw is not None else False
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        start_utc = to_utc(start) if start else None
        end_utc = to_utc(end) if end else None

        if not parcela or not parametro:
            raise ValidationError({"detail": "parcela y parametro son requeridos."})

        try:
            data = aggregate_timeseries(
                parcela_id=int(parcela),
                sensor=parametro,
                start=start_utc,
                end=end_utc,
                period=period,
                interval=interval,
                per_node=per_node
            )
        except Exception as e:
            raise ValidationError({"detail": str(e)})

        if isinstance(data, dict):
            data.setdefault("meta", {})
            data["meta"].setdefault("tz", "America/Lima")

        # IA: solo para agricultores y solo cuando no es per_node
        if role_name(user) == 'agricultor' and isinstance(data, dict) and 'points' in data and not per_node:
            summary = summarize_timeseries(data.get('meta', {}), data.get('points', []))
            if summary:
                data['explanation'] = summary

        return Response(data)

class HistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['brain'],
        summary='Historial de lecturas (agrupado)',
        description=(
            "Devuelve el historial de lecturas para una parcela agrupado por periodo.\n\n"
            "Query params:\n"
            "- parcela (required)\n"
            "- period (required): hour|day|week|month|year\n"
            "- parametro (optional): filtrar por sensor (ej. 'humedad')\n"
            "- start/end (ISO datetimes opcionales) para ventana personalizada\n"
        ),
        responses={200: TimeSeriesResponseSerializer()}
    )
    def get(self, request):
        user = request.user
        if not tiene_permiso(user, 'parcelas', 'ver'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(detail="No tiene permiso para ver historial (parcelas.ver requerido).")

        parcela = request.query_params.get('parcela')
        period = request.query_params.get('period')
        parametro = request.query_params.get('parametro')
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        start_utc = to_utc(start) if start else None
        end_utc = to_utc(end) if end else None

        if not parcela or not period:
            raise ValidationError({"detail": "parcela y period son requeridos."})

        try:
            data = fetch_history(
                int(parcela),
                period=period,
                parametro=parametro,
                start=start_utc,
                end=end_utc
            )
        except Exception as e:
            raise ValidationError({"detail": str(e)})

        return Response(data, status=status.HTTP_200_OK)

class BrainNodesLatestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['brain'],
        summary='Última medición por nodo (estado actual de la parcela)',
        description=(
            "Devuelve la última lectura disponible por nodo secundario para la parcela dada, "
            "incluyendo estado activo/inactivo según last_seen (<=10 minutos activo).\n"
            "Parámetros:\n- parcela (required)\n"
            "Incluye todos los sensores medidos por nodo (temperatura, humedad_aire, humedad_suelo, etc.)."
        ),
        parameters=[
            OpenApiParameter(name='parcela', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True),
        ],
        examples=[
            OpenApiExample(
                'Consulta correcta',
                value="/api/brain/nodes/latest/?parcela=9",
                request_only=True
            )
        ]
    )
    def get(self, request):
        from users.permissions import tiene_permiso
        if not tiene_permiso(request.user, 'parcelas', 'ver'):
            raise PermissionDenied("No tiene permiso para ver nodos de la parcela.")
        parcela = request.query_params.get('parcela')
        if not parcela:
            raise ValidationError({"detail": "parcela es requerido."})
        try:
            parcela_id = int(parcela)
        except Exception:
            raise ValidationError({"detail": "parcela inválido."})

        db = get_db()
        if db is None:
            raise ValidationError({"detail": "MongoDB no disponible."})

        # determinar maestro y secundarios de esta parcela (por modelos relacionales)
        try:
            from nodes.models import Node, NodoSecundario
            maestro = Node.objects.filter(parcela_id=parcela_id).order_by('id').first()
            maestro_codigo = maestro.codigo if maestro else None
            secundarios_qs = NodoSecundario.objects.filter(maestro=maestro) if maestro else NodoSecundario.objects.none()
            secundarios = list(secundarios_qs.values_list('codigo', flat=True))
        except Exception:
            maestro_codigo = None
            secundarios = []

        # elegir colección
        coll_name_candidates = ['lecturas_sensores', 'sensor_readings', 'readings']
        coll = None
        for n in coll_name_candidates:
            if n in db.list_collection_names():
                coll = db[n]
                break
        if coll is None:
            raise ValidationError({"detail": "Colección de lecturas no encontrada."})

        # Pipeline: última lectura POR NODO Y SENSOR (no solo por nodo)
        # Si hay lista de secundarios, se filtra por esos nodos; si no, se toma todo lo de la parcela.
        match_stage = {"parcela_id": parcela_id}
        if secundarios:
            match_stage["lecturas.nodo_codigo"] = {"$in": secundarios}

        pipeline = [
            {"$match": match_stage},
            {"$sort": {"timestamp": -1}},  # primero por documento (más reciente)
            {"$unwind": "$lecturas"},
            {"$unwind": "$lecturas.sensores"},
            {
                "$project": {
                    "nodo": "$lecturas.nodo_codigo",
                    "sensor": "$lecturas.sensores.sensor",
                    "value": "$lecturas.sensores.valor",
                    "last_seen": "$lecturas.last_seen",
                    "timestamp": {
                        "$cond": [
                            {"$eq": [{"$type": "$timestamp"}, "date"]},
                            "$timestamp",
                            {"$dateFromString": {"dateString": "$timestamp"}}
                        ]
                    }
                }
            },
            # Agrupar por (nodo, sensor) tomando el primer (más reciente) por el sort previo
            {
                "$group": {
                    "_id": {"nodo": "$nodo", "sensor": "$sensor"},
                    "last_value": {"$first": "$value"},
                    "last_seen": {"$first": "$last_seen"},
                    "last_ts": {"$first": "$timestamp"}
                }
            },
            {"$sort": {"_id.nodo": 1, "_id.sensor": 1}}
        ]

        rows = list(coll.aggregate(pipeline, allowDiskUse=True))
        now_lima = timezone.now().astimezone(LIMA_TZ)

        # construir salida por nodo con todos sus sensores
        by_node = {}
        for r in rows:
            nodo = r["_id"]["nodo"]
            sensor = r["_id"]["sensor"]
            val = r.get("last_value")
            ls = r.get("last_seen")
            ts = r.get("last_ts")

            # normalizar timestamps a Lima
            try:
                ts_local = ts.astimezone(LIMA_TZ) if hasattr(ts, 'astimezone') else None
            except Exception:
                ts_local = None
            try:
                ls_local = ls.astimezone(LIMA_TZ) if hasattr(ls, 'astimezone') and ls is not None else ts_local
            except Exception:
                ls_local = ts_local

            node_entry = by_node.setdefault(nodo, {
                "nodo": nodo,
                "last_seen": (ls_local.isoformat() if ls_local else (ts_local.isoformat() if ts_local else None)),
                "activo": False,
                "sensores": {}
            })
            node_entry["sensores"][sensor] = val

            # estado activo si last_seen dentro de 10 minutos
            if ls_local:
                delta = now_lima - ls_local
                node_entry["activo"] = (delta.total_seconds() <= 600)

        # si se conocen secundarios, incluir nodos sin lecturas recientes con sensores vacíos
        for codigo in secundarios:
            by_node.setdefault(codigo, {
                "nodo": codigo,
                "last_seen": None,
                "activo": False,
                "sensores": {}
            })

        result = list(by_node.values())

        return Response({
            "parcela_id": parcela_id,
            "nodo_maestro": maestro_codigo,
            "nodos_secundarios": secundarios,
            "timestamp_generado": now_lima.isoformat(),
            "nodos": result
        }, status=status.HTTP_200_OK)

class BrainKPIsUnifiedView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, parcela_id: int = None):
        user = request.user
        if not tiene_permiso(user, 'parcelas', 'ver'):
            raise PermissionDenied("parcelas.ver requerido.")

        if parcela_id is None:
            try:
                from parcels.models import Parcela
                from nodes.models import Node, NodoSecundario
                from tasks.models import Task
                from authentication.models import User
                from users.models import Rol, Prospecto
            except Exception:
                Parcela = Node = NodoSecundario = Task = User = Rol = Prospecto = None

            now_lima = timezone.now().astimezone(LIMA_TZ).isoformat()
            rname = (role_name(user) or '').lower()

            # Modo admin/superadmin: KPIs del sistema
            if rname in ('administrador', 'superadmin'):
                total_parcelas_sys = Parcela.objects.count() if Parcela else 0

                # Ids de roles relevantes
                rol_agricultor_id = Rol.objects.filter(nombre__iexact='agricultor').values_list('id', flat=True).first() if Rol else None
                rol_tecnico_id = Rol.objects.filter(nombre__iexact='tecnico').values_list('id', flat=True).first() if Rol else None
                rol_admin_id = Rol.objects.filter(nombre__iexact='administrador').values_list('id', flat=True).first() if Rol else None
                rol_super_id = Rol.objects.filter(nombre__iexact='superadmin').values_list('id', flat=True).first() if Rol else None

                total_agricultores = User.objects.filter(rol_id=rol_agricultor_id).count() if (User and rol_agricultor_id) else 0
                total_tecnicos = User.objects.filter(rol_id=rol_tecnico_id).count() if (User and rol_tecnico_id) else 0
                total_administradores = User.objects.filter(rol_id__in=[x for x in [rol_admin_id, rol_super_id] if x]).count() if User else 0
                total_prospectos = Prospecto.objects.count() if Prospecto else 0
                total_nodos_sys = Node.objects.count() if Node else 0
                total_secundarios_sys = NodoSecundario.objects.count() if NodoSecundario else 0

                return Response({
                    "owner_id": user.id,
                    "fecha_actualizacion": now_lima,
                    "parametros": [
                        {"nombre": "Agricultores", "valor": total_agricultores},
                        {"nombre": "Técnicos", "valor": total_tecnicos},
                        {"nombre": "Administradores", "valor": total_administradores},
                        {"nombre": "Parcelas (Total)", "valor": total_parcelas_sys},
                        {"nombre": "Prospectos", "valor": total_prospectos},
                        {"nombre": "Nodos", "valor": total_nodos_sys},
                        {"nombre": "Nodos Secundarios", "valor": total_secundarios_sys},
                    ]
                }, status=status.HTTP_200_OK)

            # Modo usuario no admin: KPIs personales
            parcelas_qs = Parcela.objects.filter(usuario_id=user.id) if Parcela else []
            total_parcelas = parcelas_qs.count() if Parcela else 0

            if Node and total_parcelas:
                nodos_maestros_qs = Node.objects.filter(parcela__in=parcelas_qs)
                total_nodos = nodos_maestros_qs.count()
            else:
                total_nodos = 0
                nodos_maestros_qs = []

            if NodoSecundario and total_nodos:
                total_secundarios = NodoSecundario.objects.filter(maestro__in=nodos_maestros_qs).count()
            else:
                total_secundarios = 0

            if Task and total_parcelas:
                tareas_pendientes = Task.objects.filter(
                    parcela__in=parcelas_qs,
                    estado__in=['pendiente', 'en_progreso']
                ).count()
                total_alertas = Task.objects.filter(
                    parcela__in=parcelas_qs,
                    estado='vencida'
                ).count()
            else:
                tareas_pendientes = 0
                total_alertas = 0

            return Response({
                "owner_id": user.id,
                "fecha_actualizacion": now_lima,
                "parametros": [
                    {"nombre": "Parcelas", "valor": total_parcelas},
                    {"nombre": "Nodos", "valor": total_nodos},
                    {"nombre": "Nodos Secundarios", "valor": total_secundarios},
                    {"nombre": "Tareas Pendientes", "valor": tareas_pendientes},
                    {"nombre": "Alertas", "valor": total_alertas},
                ]
            }, status=status.HTTP_200_OK)

        # Modo por parcela
        # Nombre de parcela y métricas operativas
        try:
            from parcelas.models import Parcela
            parcela = Parcela.objects.get(pk=parcela_id)
            nombre_parcela = parcela.nombre
        except Exception:
            nombre_parcela = f"Parcela {parcela_id}"

        db = get_db()
        if db is None:
            raise ValidationError({"detail": "MongoDB no disponible."})

        latest = _latest_secondary_nodes_for_parcela(db, int(parcela_id))
        now_lima = timezone.now().astimezone(LIMA_TZ)

        # Agrupar por nodo activo (last_seen <=10min)
        activos = {}
        for r in latest:
            nodo = r["_id"]["nodo"]
            ls = r.get("last_seen")
            try:
                ls_local = ls.astimezone(LIMA_TZ) if hasattr(ls, 'astimezone') and ls is not None else None
            except Exception:
                ls_local = None
            activo = False
            if ls_local:
                delta = now_lima - ls_local
                activo = (delta.total_seconds() <= 600)
            if activo:
                entry = activos.setdefault(nodo, {})
                sensor = r["_id"]["sensor"]
                entry[sensor] = {
                    "valor": r.get("last_value"),
                    "fecha": r.get("last_ts"),
                }

        # Promedios ambientales sobre nodos activos
        def promedio_sensor(sensor_key):
            vals = []
            fechas = []
            for node, sensors in activos.items():
                if sensor_key in sensors and sensors[sensor_key]["valor"] is not None:
                    vals.append(float(sensors[sensor_key]["valor"]))
                    fechas.append(sensors[sensor_key]["fecha"])
            if not vals:
                return None, None
            avg = sum(vals) / len(vals)
            # fecha más reciente
            fechas_lima = []
            for f in fechas:
                try:
                    fechas_lima.append(f.astimezone(LIMA_TZ) if hasattr(f, 'astimezone') else None)
                except Exception:
                    fechas_lima.append(None)
            fecha = max([x for x in fechas_lima if x is not None], default=None)
            return avg, fecha

        # métricas operativas (reemplaza por tus modelos reales si los tienes)
        nodos_totales = len({r["_id"]["nodo"] for r in latest})
        nodos_secundarios = len(activos.keys())  # activos como proxy
        tareas_pendientes = 0  # TODO: contar tareas pendientes de esta parcela
        # alertas: cantidad de parámetros con estado peligro (se computa tras ambientales)

        parametros = [
            {"nombre": "Nodos", "valor": nodos_totales},
            {"nombre": "Nodos Secundarios", "valor": nodos_secundarios},
            {"nombre": "Tareas Pendientes", "valor": tareas_pendientes},
            # Alertas se agrega al final cuando tengamos estados
        ]

        peligro_count = 0
        # Temperatura
        temp_val, temp_fecha = promedio_sensor("temperatura")
        limits = ENV_LIMITS["temperatura"]
        estado = _estado_parametro(temp_val, limits)
        if estado == "peligro":
            peligro_count += 1
        parametros.append({
            "nombre": limits["label"],
            "valor": temp_val,
            "unidad": limits["unidad"],
            "fecha": (temp_fecha.isoformat() if temp_fecha else None),
            "limites": {"min": limits["min"], "max": limits["max"]},
            "estado": estado,
        })

        # Humedad del Suelo
        hs_val, hs_fecha = promedio_sensor("humedad_suelo")
        limits = ENV_LIMITS["humedad_suelo"]
        estado = _estado_parametro(hs_val, limits)
        if estado == "peligro":
            peligro_count += 1
        parametros.append({
            "nombre": limits["label"],
            "valor": hs_val,
            "unidad": limits["unidad"],
            "fecha": (hs_fecha.isoformat() if hs_fecha else None),
            "limites": {"min": limits["min"], "max": limits["max"]},
            "estado": estado,
        })

        # Humedad del Aire
        ha_val, ha_fecha = promedio_sensor("humedad_aire")
        limits = ENV_LIMITS["humedad_aire"]
        estado = _estado_parametro(ha_val, limits)
        if estado == "peligro":
            peligro_count += 1
        parametros.append({
            "nombre": limits["label"],
            "valor": ha_val,
            "unidad": limits["unidad"],
            "fecha": (ha_fecha.isoformat() if ha_fecha else None),
            "limites": {"min": limits["min"], "max": limits["max"]},
            "estado": estado,
        })

        # Alertas al final
        parametros.append({"nombre": "Alertas", "valor": peligro_count})

        return Response({
            "parcela_id": int(parcela_id),
            "nombre": nombre_parcela,
            "fecha_ultima_actualizacion": now_lima.isoformat(),
            "parametros": parametros
        }, status=status.HTTP_200_OK)

class AuditSeriesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Solo admin/superadmin
        rname = (role_name(request.user) or '').lower()
        if rname not in ('administrador', 'superadmin') or not tiene_permiso(request.user, 'administracion', 'ver'):
            raise PermissionDenied('administracion.ver requerido')
        event = (request.query_params.get('event') or '').lower() or 'login'
        period = (request.query_params.get('period') or 'day').lower()  # 'hour' | 'day'
        user_id = request.query_params.get('user')

        qs = AuditLog.objects.filter(event=event)
        if user_id:
            qs = qs.filter(user_id=int(user_id))

        trunc = TruncHour if period == 'hour' else TruncDay
        agg = qs.annotate(bucket=trunc('created_at')).values('bucket').annotate(count=Count('id')).order_by('bucket')
        points = [{"timestamp": r['bucket'], "count": r['count']} for r in agg]
        return Response({"event": event, "period": period, "points": points}, status=status.HTTP_200_OK)

class AuditHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Solo admin/superadmin
        rname = (role_name(request.user) or '').lower()
        if rname not in ('administrador', 'superadmin') or not tiene_permiso(request.user, 'administracion', 'ver'):
            raise PermissionDenied('administracion.ver requerido')

        event = (request.query_params.get('event') or '').lower() or None
        user_id = request.query_params.get('user')
        start = request.query_params.get('start')  # ISO
        end = request.query_params.get('end')

        qs = AuditLog.objects.all().order_by('-created_at')
        if event:
            qs = qs.filter(event=event)
        if user_id:
            qs = qs.filter(user_id=int(user_id))
        if start:
            qs = qs.filter(created_at__gte=start)
        if end:
            qs = qs.filter(created_at__lte=end)

        data = [{
            "user_id": x.user_id,
            "event": x.event,
            "module": x.module,
            "action": x.action,
            "metadata": x.metadata,
            "created_at": x.created_at,
        } for x in qs[:1000]]  # límite de respuesta
        return Response(data, status=status.HTTP_200_OK)
