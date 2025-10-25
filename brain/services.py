from datetime import timedelta
from typing import Dict, Any, List
from django.utils import timezone
from django.db.models import Avg, Count

# intento de reusar conexión a Mongo centralizada
try:
    from agro_ai_platform.mongo import get_db
except Exception:
    # fallback que devuelve None si no existe el módulo (permite pruebas locales)
    def get_db():
        return None

# nuevo: importar Task y modelos de reglas/parcelas
try:
    from tasks.models import Task
except Exception:
    Task = None

try:
    from parcels.models import Parcela, Etapa, ReglaPorEtapa
except Exception:
    Parcela = Etapa = ReglaPorEtapa = None

# helper para truncar timestamps en Python (fallback)
def _truncate_dt(dt, bucket: str):
    if bucket == 'minute':
        return dt.replace(second=0, microsecond=0)
    if bucket == 'hour':
        return dt.replace(minute=0, second=0, microsecond=0)
    if bucket == 'day':
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if bucket == 'month':
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if bucket == 'year':
        return dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return dt

def aggregate_timeseries(parcela_id: int, parametro: str,
                         period: str = 'day',
                         interval: str | None = None,
                         start=None, end=None) -> Dict[str, Any]:
    """
    Devuelve puntos agregados (avg) para un parámetro de una parcela.
    - period: 'hour'|'day'|'week'|'month'|'year' (ventana por defecto)
    - interval: bucket: 'minute'|'hour'|'day'|'month'|'year'
    - start/end: datetimes (si None se calcula en base a period)
    """
    now = timezone.now()
    if end is None:
        end = now
    if start is None:
        deltas = {'hour': timedelta(hours=1), 'day': timedelta(days=1), 'week': timedelta(days=7),
                  'month': timedelta(days=30), 'year': timedelta(days=365)}
        start = end - deltas.get(period, timedelta(days=1))

    # elegir bucket por defecto
    default_bucket = {'hour': 'minute', 'day': 'hour', 'week': 'day', 'month': 'day', 'year': 'month'}
    bucket = interval or default_bucket.get(period, 'hour')

    db = get_db()
    if db is None:
        raise RuntimeError("MongoDB no disponible: configura MONGO_URL/MONGO_DB y agro_ai_platform.mongo.get_db()")

    # elegir colección existente
    coll_name_candidates = ['sensor_readings', 'lecturas_sensores', 'readings']
    coll = None
    for n in coll_name_candidates:
        if n in db.list_collection_names():
            coll = db[n]
            break
    if coll is None:
        raise RuntimeError("Colección de lecturas no encontrada en MongoDB (sensor_readings / lecturas_sensores).")

    # intentamos pipeline con $dateTrunc (Mongo 5+)
    try:
        from pymongo import ASCENDING
        pipeline = [
            {"$match": {"parcela_id": parcela_id,
                        "timestamp": {"$gte": start, "$lte": end}}},
            {"$unwind": "$lecturas"},
            {"$unwind": "$lecturas.sensores"},
            {"$match": {"lecturas.sensores.sensor": parametro}},
            {"$project": {
                "timestamp": {"$cond": [
                    {"$isDate": "$timestamp"}, "$timestamp", {"$toDate": "$timestamp"}
                ]},
                "value": "$lecturas.sensores.valor"
            }},
            {"$group": {
                "_id": {"$dateTrunc": {"date": "$timestamp", "unit": bucket}},
                "avg": {"$avg": "$value"}
            }},
            {"$sort": {"_id": ASCENDING}}
        ]
        agg = list(coll.aggregate(pipeline, allowDiskUse=True))
        points = [{"timestamp": (row["_id"].isoformat() if row["_id"] is not None else None),
                   "value": float(row["avg"]) if row.get("avg") is not None else None} for row in agg]
        meta = {"parcela_id": parcela_id, "parametro": parametro, "start": start.isoformat(), "end": end.isoformat(), "bucket": bucket, "points_count": len(points)}
        return {"meta": meta, "points": points}
    except Exception:
        # fallback: agrupar en Python
        from dateutil.parser import isoparse
        cursor = coll.find({"parcela_id": parcela_id}, projection=["timestamp", "lecturas"])
        buckets = {}
        for doc in cursor:
            ts = doc.get("timestamp")
            try:
                ts_dt = isoparse(ts) if isinstance(ts, str) else ts
            except Exception:
                continue
            if ts_dt < start or ts_dt > end:
                continue
            for lectura in doc.get("lecturas", []):
                for sensor in lectura.get("sensores", []):
                    if sensor.get("sensor") != parametro:
                        continue
                    val = sensor.get("valor")
                    key_dt = _truncate_dt(ts_dt, bucket)
                    buckets.setdefault(key_dt, []).append(float(val))
        points = [{"timestamp": k.isoformat(), "value": (sum(v)/len(v) if v else None)} for k, v in sorted(buckets.items())]
        meta = {"parcela_id": parcela_id, "parametro": parametro, "start": start.isoformat(), "end": end.isoformat(), "bucket": bucket, "points_count": len(points)}
        return {"meta": meta, "points": points}
 
def fetch_history(parcela_id: int,
                  period: str = 'day',
                  parametro: str | None = None,
                  start=None,
                  end=None,
                  limit_examples_per_bucket: int = 20) -> Dict[str, Any]:
    """
    Devuelve historial agrupado por bucket con ejemplos de lecturas.
    - period: 'hour'|'day'|'week'|'month'|'year'
    - parametro: opcional para filtrar sensor
    """
    # reutiliza lógica de ventanas similar a aggregate_timeseries
    now = timezone.now()
    if end is None:
        end = now
    deltas = {
        'hour': timedelta(hours=1),
        'day': timedelta(days=1),
        'week': timedelta(days=7),
        'month': timedelta(days=30),
        'year': timedelta(days=365)
    }
    start = start or (end - deltas.get(period, timedelta(days=1)))

    # bucket de ejemplo para history (más granular para inspección)
    if period == 'hour':
        bucket = 'minute'
    elif period in ('day', 'week'):
        bucket = 'hour'
    elif period == 'month':
        bucket = 'day'
    elif period == 'year':
        bucket = 'month'
    else:
        bucket = 'hour'

    db = get_db()
    if db is None:
        raise RuntimeError("MongoDB no disponible: configura MONGO_URL/MONGO_DB y agro_ai_platform.mongo.get_db()")

    coll_name_candidates = ['sensor_readings', 'lecturas_sensores', 'readings']
    coll = None
    for n in coll_name_candidates:
        if n in db.list_collection_names():
            coll = db[n]
            break
    if coll is None:
        raise RuntimeError("Colección de lecturas no encontrada en MongoDB (sensor_readings / lecturas_sensores).")

    from dateutil.parser import isoparse
    cursor = coll.find(
        {"parcela_id": parcela_id},
        projection=["timestamp", "codigo_nodo_maestro", "lecturas"]
    ).sort("timestamp", 1)

    buckets = {}
    for doc in cursor:
        ts = doc.get("timestamp")
        try:
            ts_dt = isoparse(ts) if isinstance(ts, str) else ts
        except Exception:
            continue
        if ts_dt < start or ts_dt > end:
            continue
        # key truncation
        key_dt = _truncate_dt(ts_dt, bucket)
        bucket_key = key_dt.isoformat()
        for lectura in doc.get("lecturas", []):
            nodo_codigo = lectura.get("nodo_codigo")
            for sensor in lectura.get("sensores", []):
                sname = sensor.get("sensor")
                if parametro and sname != parametro:
                    continue
                example = {
                    "timestamp": ts_dt.isoformat(),
                    "codigo_nodo_maestro": doc.get("codigo_nodo_maestro"),
                    "nodo_codigo": nodo_codigo,
                    "sensor": sname,
                    "valor": sensor.get("valor"),
                    "unidad": sensor.get("unidad"),
                }
                lst = buckets.setdefault(bucket_key, [])
                lst.append(example)

    bucket_items = []
    for k in sorted(buckets.keys()):
        values = buckets[k]
        bucket_items.append({
            "bucket": k,
            "count": len(values),
            "examples": values[:limit_examples_per_bucket]
        })

    meta = {
        "parcela_id": parcela_id,
        "parametro": parametro,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "bucket": bucket,
        "buckets_count": len(bucket_items)
    }
    return {"meta": meta, "buckets": bucket_items}

def compute_kpis_for_user(user) -> Dict[str, Any]:
    """
    Función simple role-aware para devolver KPIs.
    - administradores -> KPIs globales
    - otros roles -> KPIs sobre sus parcelas
    """
    from users.permissions import role_name
    r = role_name(user)

    # helper seguro si no hay modelos disponibles
    def empty_kpis(scope='user'):
        return {"scope": scope, "total_parcelas": 0, "parcelas_sin_etapa": 0, "avg_tamano_hectareas": None}

    if Parcela is None:
        return empty_kpis(scope='global' if r in ('superadmin','administrador') else 'user')

    if r in ('superadmin', 'administrador'):
        qs = Parcela.objects.all()
        total_parcelas = qs.count()
        parcelas_sin_etapa = qs.filter(etapa_actual__isnull=True).count()
        avg_tamano = qs.aggregate(avg=Avg('tamano_hectareas'))['avg']
        reglas_activas = ReglaPorEtapa.objects.filter(activo=True).count() if ReglaPorEtapa is not None else 0
        etapas_totales = Etapa.objects.count() if Etapa is not None else 0
        parcelas_por_cultivo = list(qs.values('cultivo__nombre').annotate(count=Count('id')).order_by('-count'))
        return {
            "scope": "global",
            "total_parcelas": total_parcelas,
            "parcelas_sin_etapa": parcelas_sin_etapa,
            "avg_tamano_hectareas": float(avg_tamano) if avg_tamano is not None else None,
            "reglas_activas": reglas_activas,
            "etapas_totales": etapas_totales,
            "parcelas_por_cultivo": parcelas_por_cultivo,
        }

    # rol agricultor / tecnico / otros -> KPIs por usuario
    qs = Parcela.objects.filter(usuario=user)
    total_parcelas = qs.count()
    parcelas_sin_etapa = qs.filter(etapa_actual__isnull=True).count()
    parcelas_con_etapa = qs.exclude(etapa_actual__isnull=True).count()
    avg_tamano = qs.aggregate(avg=Avg('tamano_hectareas'))['avg']
    reglas_qs = ReglaPorEtapa.objects.filter(etapa__parcela__usuario=user, activo=True).distinct() if ReglaPorEtapa is not None else []
    reglas_relevantes = reglas_qs.count() if hasattr(reglas_qs, 'count') else 0
    parcelas_por_cultivo = list(qs.values('cultivo__nombre').annotate(count=Count('id')).order_by('-count'))
    etapas_distribution = list(qs.values('etapa_actual__nombre').annotate(count=Count('id')).order_by('-count'))
    return {
        "scope": "user",
        "total_parcelas": total_parcelas,
        "parcelas_con_etapa": parcelas_con_etapa,
        "parcelas_sin_etapa": parcelas_sin_etapa,
        "avg_tamano_hectareas": float(avg_tamano) if avg_tamano is not None else None,
        "reglas_relevantes": reglas_relevantes,
        "parcelas_por_cultivo": parcelas_por_cultivo,
        "etapas_distribution": etapas_distribution,
    }

def evaluate_rules_and_create_tasks_for_parcela(parcela_id: int, lookback_minutes: int = 60) -> Dict[str, Any]:
    """
    Evalúa las reglas aplicables a la parcela (por su etapa actual / etapa asociada)
    y crea tareas recomendadas (origen='ia') cuando una lectura viola una regla.

    - Evita duplicados usando recommend_origin_id = "rule:{rule.id}:last:{timestamp_iso}".
    - Retorna resumen con tareas creadas y reglas evaluadas.
    """
    now = timezone.now()
    results = {"parcela_id": parcela_id, "evaluated": 0, "created_tasks": []}

    if ReglaPorEtapa is None or Parcela is None or Task is None:
        results["error"] = "Modelos ReglaPorEtapa/Parcela/Task no disponibles"
        return results

    try:
        parcela = Parcela.objects.select_related('etapa_actual').get(pk=parcela_id)
    except Parcela.DoesNotExist:
        results["error"] = "Parcela no encontrada"
        return results

    # determinar reglas aplicables: priorizamos etapa_actual si existe, si no reglas globales para la variedad
    reglas_qs = ReglaPorEtapa.objects.filter(activo=True)
    if getattr(parcela, 'etapa_actual', None):
        reglas_qs = reglas_qs.filter(etapa=parcela.etapa_actual)
    else:
        # fallback: reglas para la variedad / cultivo de la parcela
        if getattr(parcela, 'variedad', None):
            reglas_qs = reglas_qs.filter(etapa__variedad=parcela.variedad)
        else:
            reglas_qs = reglas_qs.none()

    db = get_db()
    if db is None:
        results["error"] = "MongoDB no disponible"
        return results

    coll_name_candidates = ['lecturas_sensores', 'sensor_readings', 'readings']
    coll = None
    for n in coll_name_candidates:
        if n in db.list_collection_names():
            coll = db[n]
            break
    if coll is None:
        results["error"] = "Colección lecturas no encontrada en MongoDB"
        return results

    # lookback window
    cutoff = now - timedelta(minutes=lookback_minutes)

    for regla in reglas_qs:
        results["evaluated"] += 1
        parametro = getattr(regla, 'parametro', None)
        if not parametro:
            continue

        # obtener la última lectura para este parámetro y parcela (pipeline robusto)
        try:
            pipeline = [
                {"$match": {"parcela_id": parcela_id, "timestamp": {"$gte": cutoff}}},
                {"$unwind": "$lecturas"},
                {"$unwind": "$lecturas.sensores"},
                {"$match": {"lecturas.sensores.sensor": parametro}},
                {"$project": {
                    "timestamp": {"$cond": [{"$isDate": "$timestamp"}, "$timestamp", {"$toDate": "$timestamp"}]},
                    "value": "$lecturas.sensores.valor",
                    "nodo_codigo": "$lecturas.nodo_codigo",
                    "codigo_nodo_maestro": "$codigo_nodo_maestro"
                }},
                {"$sort": {"timestamp": -1}},
                {"$limit": 1}
            ]
            doc = list(coll.aggregate(pipeline, allowDiskUse=True))
            last = doc[0] if doc else None
        except Exception:
            # fallback simple: buscar doc ordenado por timestamp y deshacer unwind manual (menos eficiente)
            last = None
            try:
                cursor = coll.find({"parcela_id": parcela_id, "timestamp": {"$gte": cutoff}}).sort("timestamp", -1).limit(50)
                for d in cursor:
                    for lectura in d.get("lecturas", []):
                        for s in lectura.get("sensores", []):
                            if s.get("sensor") == parametro:
                                last = {
                                    "timestamp": d.get("timestamp"),
                                    "value": s.get("valor"),
                                    "nodo_codigo": lectura.get("nodo_codigo"),
                                    "codigo_nodo_maestro": d.get("codigo_nodo_maestro")
                                }
                                break
                        if last:
                            break
                    if last:
                        break
            except Exception:
                last = None

        if not last:
            continue

        try:
            value = float(last.get("value"))
        except Exception:
            continue

        # decidir si viola regla
        minimo = getattr(regla, 'minimo', None)
        maximo = getattr(regla, 'maximo', None)
        accion = None
        motivo = None

        if minimo is not None and value < float(minimo):
            accion = getattr(regla, 'accion_si_menor', None)
            motivo = "valor_menor_que_minimo"
        elif maximo is not None and value > float(maximo):
            accion = getattr(regla, 'accion_si_mayor', None)
            motivo = "valor_mayor_que_maximo"

        if not accion:
            continue

        # crear origen_id para idempotencia: regla:ID + timestamp lectura (iso) = único por evento
        ts = last.get("timestamp")
        ts_iso = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)
        origen_id = f"rule:{regla.id}:last:{ts_iso}"

        # evitar duplicados: si ya existe una tarea activa con este origen_id y decision pend/aceptada, no duplicar
        exists_qs = Task.all_objects.filter(recomendacion_origen_id=origen_id)
        if exists_qs.exists():
            # Si hay alguna existente activa/no eliminada, saltar
            if exists_qs.filter(deleted_at__isnull=True).exists():
                continue

        # preparar descripción/snapshot
        descripcion = f"{accion} (regla {regla.id}) — parametro={parametro}, valor={value}, min={minimo}, max={maximo}, nodo={last.get('nodo_codigo')}"
        snapshot = {
            "rule_id": regla.id,
            "parametro": parametro,
            "valor": value,
            "minimo": minimo,
            "maximo": maximo,
            "accion": accion,
            "timestamp_lectura": ts_iso,
            "nodo_codigo": last.get("nodo_codigo"),
            "codigo_nodo_maestro": last.get("codigo_nodo_maestro"),
            "motivo": motivo
        }

        # fecha_programada: por defecto ahora + 1 hora (puedes ajustar)
        fecha_programada = timezone.now() + timedelta(hours=1)

        # crear tarea recomendada (usar helper si existe)
        try:
            if hasattr(Task, "create_recommended"):
                tarea = Task.create_recommended(
                    parcela=parcela,
                    tipo=str(accion)[:50],
                    descripcion=descripcion,
                    fecha_programada=fecha_programada,
                )
                # rellenar campos adicionales (snapshot + origen_id + origen/decision)
                tarea.recomendacion_snapshot = snapshot
                tarea.recomendacion_origen_id = origen_id
                tarea.origen = 'ia'
                tarea.decision = 'pendiente'
                tarea.recomendacion_aceptada = None
                tarea.save()
            else:
                tarea = Task.all_objects.create(
                    parcela=parcela,
                    tipo=str(accion)[:50],
                    descripcion=descripcion,
                    fecha_programada=fecha_programada,
                    origen='ia',
                    decision='pendiente',
                    recomendacion_snapshot=snapshot,
                    recomendacion_origen_id=origen_id
                )
        except Exception as e:
            # no interrumpir el loop por error en creación
            continue

        results["created_tasks"].append({"task_id": getattr(tarea, 'id', None), "origen_id": origen_id, "rule_id": regla.id})

    return results