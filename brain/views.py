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
from users.permissions import tiene_permiso
from django.utils.dateparse import parse_datetime
from agro_ai_platform.mongo import to_utc, LIMA_TZ, get_db
from django.utils import timezone  # <-- requerido para timezone.now() en BrainNodesLatestView

@extend_schema(
    tags=['brain'],
    summary='KPIs del sistema / usuario',
    description=(
        "Devuelve KPIs.\n\n"
        "- type=summary (default): KPIs resumidos globales/usuario.\n"
        "- type=daily: KPIs diarios (solo datos de hoy). "
        "Con ?parcela=ID devuelve esa parcela; sin parcela devuelve todas y el KPI general.\n"
    ),
    parameters=[
        OpenApiParameter(name='type', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False,
                         description="summary | daily"),
        OpenApiParameter(name='parcela', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False,
                         description="ID de parcela (solo para type=daily)"),
    ],
    responses={
        200: KPISerializer,
        200: DailyUserKPISerializer
    }
)
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

        # opcional: anexa tz meta
        if isinstance(data, dict):
            data.setdefault("meta", {})
            data["meta"].setdefault("tz", "America/Lima")
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
        ),
        parameters=[
            OpenApiParameter(name='parcela', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True),
        ],
        examples=[
            OpenApiExample(
                'Ejemplo de respuesta',
                value={
                    "parcela_id": 2,
                    "timestamp_generado": "2025-12-01T12:30:00-05:00",
                    "nodos": [
                        {"nodo": "NODE-02-S1", "last_seen": "2025-12-01T12:29:55-05:00", "activo": True, "sensores": {"temperatura": 21.8, "humedad": 58.1}},
                        {"nodo": "NODE-02-S2", "last_seen": "2025-12-01T12:20:12-05:00", "activo": True, "sensores": {"temperatura": 22.0}},
                        {"nodo": "NODE-02-S3", "last_seen": None, "activo": False, "sensores": {}},
                    ]
                },
                response_only=True
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

        coll_name_candidates = ['lecturas_sensores', 'sensor_readings', 'readings']
        coll = None
        for n in coll_name_candidates:
            if n in db.list_collection_names():
                coll = db[n]
                break
        if coll is None:
            raise ValidationError({"detail": "Colección de lecturas no encontrada."})

        pipeline = [
            {"$match": {"parcela_id": parcela_id}},
            {"$unwind": "$lecturas"},
            {"$sort": {"timestamp": -1}},
            {
                "$group": {
                    "_id": "$lecturas.nodo_codigo",
                    "ultimo_doc": {"$first": "$$ROOT"},
                    "ultimo_read": {"$first": "$lecturas"}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "nodo": "$_id",
                    # Antes: "$cond": [{"$isDate": ...}, ...]  -> rompe en versiones sin $isDate
                    "timestamp": {
                        "$cond": [
                            {"$eq": [{"$type": "$ultimo_doc.timestamp"}, "date"]},
                            "$ultimo_doc.timestamp",
                            {"$dateFromString": {"dateString": "$ultimo_doc.timestamp"}}
                        ]
                    },
                    "last_seen": "$ultimo_read.last_seen",
                    "sensores": "$ultimo_read.sensores"
                }
            }
        ]

        docs = list(coll.aggregate(pipeline, allowDiskUse=True))
        now_lima = timezone.now().astimezone(LIMA_TZ)

        result = []
        for d in docs:
            ts_doc = d.get("timestamp")
            ls = d.get("last_seen")
            # normalizar a Lima
            try:
                ts_local = ts_doc.astimezone(LIMA_TZ) if hasattr(ts_doc, 'astimezone') else None
            except Exception:
                ts_local = None
            try:
                ls_local = ls.astimezone(LIMA_TZ) if hasattr(ls, 'astimezone') and ls is not None else ts_local
            except Exception:
                ls_local = ts_local
            activo = False
            if ls_local:
                delta = now_lima - ls_local
                activo = (delta.total_seconds() <= 600)  # 10 minutos

            sensores_dict = {}
            for s in d.get("sensores") or []:
                name = s.get("sensor")
                val = s.get("valor")
                if name is not None:
                    sensores_dict[name] = val

            result.append({
                "nodo": d.get("nodo"),
                "last_seen": (ls_local.isoformat() if ls_local else None),
                "activo": activo,
                "sensores": sensores_dict
            })

        return Response({
            "parcela_id": parcela_id,
            "timestamp_generado": now_lima.isoformat(),
            "nodos": result
        }, status=status.HTTP_200_OK)
