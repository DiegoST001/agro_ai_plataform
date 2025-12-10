from datetime import datetime, timedelta
from typing import Dict, Any, List
from django.utils import timezone
from django.db.models import Avg, Count
from agro_ai_platform.mongo import get_db, to_utc, to_lima, UTC, LIMA_TZ

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
    from parcels.models import Parcela, Ciclo
except ImportError:
    Parcela = None
    Ciclo = None
try:
    from crops.models import ReglaPorEtapa
except ImportError:
    ReglaPorEtapa = None
# >>> FALTA importar Etapa para KPIs globales
try:
    from crops.models import Etapa
except ImportError:
    Etapa = None

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

def aggregate_timeseries(parcela_id, sensor, start=None, end=None, period='day', interval='auto', per_node: bool = False):
    db = get_db()
    start_utc = to_utc(start) if start else None
    end_utc = to_utc(end) if end else None

    match = {"parcela_id": int(parcela_id)}
    if start_utc or end_utc:
        match["timestamp"] = {}
        if start_utc:
            match["timestamp"]["$gte"] = start_utc
        if end_utc:
            match["timestamp"]["$lte"] = end_utc

    coll = db.get_collection("lecturas_sensores") if "lecturas_sensores" in db.list_collection_names() else db.get_collection("readings")

    try:
        pipeline = [
            {"$match": match},
            {"$unwind": "$lecturas"},
            {"$unwind": "$lecturas.sensores"},
            {"$match": {"lecturas.sensores.sensor": sensor}},
            {
                "$addFields": {
                    "bucket": {
                        "$dateTrunc": {
                            "date": {"$cond": [{"$eq": [{"$type": "$timestamp"}, "date"]}, "$timestamp", {"$dateFromString": {"dateString": "$timestamp"}}]},
                            "unit": period,  # minute|hour|day|week|month|year
                            "binSize": (1 if interval == "auto" else int(interval)),
                            "timezone": "America/Lima"
                        }
                    },
                    "value": "$lecturas.sensores.valor"
                }
            },
        ]

        if per_node:
            # Agrupar por nodo y bucket, sin promediar entre nodos (promedia solo dentro del mismo nodo cuando hay múltiples lecturas en el bucket)
            pipeline += [
                {
                    "$group": {
                        "_id": {"bucket": "$bucket", "nodo": "$lecturas.nodo_codigo"},
                        "value": {"$avg": "$value"}
                    }
                },
                {"$sort": {"_id.bucket": 1, "_id.nodo": 1}}
            ]
        else:
            # Promediar por bucket entre todos los nodos (un solo punto por bucket)
            pipeline += [
                {
                    "$group": {
                        "_id": "$bucket",
                        "value": {"$avg": "$value"}
                    }
                },
                {"$sort": {"_id": 1}}
            ]

        agg = list(coll.aggregate(pipeline, allowDiskUse=True))

        if per_node:
            series_map = {}
            for row in agg:
                bucket_dt = row["_id"]["bucket"]
                nodo = row["_id"]["nodo"]
                if bucket_dt is None or nodo is None:
                    continue
                pt = {
                    "timestamp": bucket_dt.isoformat(),
                    "value": (float(row["value"]) if row.get("value") is not None else None)
                }
                series_map.setdefault(nodo, []).append(pt)
            series = [{"nodo": k, "points": v} for k, v in series_map.items()]
            meta = {
                "parcela_id": parcela_id,
                "parametro": sensor,
                "start": (start_utc.isoformat() if start_utc else None),
                "end": (end_utc.isoformat() if end_utc else None),
                "bucket": period,
                "tz": "America/Lima",
                "type": "per_node",
                "series_count": len(series)
            }
            return {"meta": meta, "series": series}

        points = [
            {
                "timestamp": (row["_id"].isoformat() if row.get("_id") is not None else None),
                "value": (float(row["value"]) if row.get("value") is not None else None)
            }
            for row in agg
        ]
        meta = {
            "parcela_id": parcela_id,
            "parametro": sensor,
            "start": (start_utc.isoformat() if start_utc else None),
            "end": (end_utc.isoformat() if end_utc else None),
            "bucket": period,
            "tz": "America/Lima",
            "points_count": len(points)
        }
        return {"meta": meta, "points": points}
    except Exception:
        # Fallback Python: proteger comparaciones None y aplicar promedio entre nodos para per_node=false
        cursor = coll.find({"parcela_id": int(parcela_id)}, projection=["timestamp", "lecturas"])
        if per_node:
            node_buckets = {}
        else:
            buckets = {}
        for doc in cursor:
            ts_dt = doc.get("timestamp")
            # Normalizar timestamp a aware UTC
            try:
                ts_dt = to_utc(ts_dt)
            except Exception:
                continue
            if start_utc and ts_dt < start_utc:
                continue
            if end_utc and ts_dt > end_utc:
                continue
            for lectura in doc.get("lecturas", []):
                nodo_code = lectura.get("nodo_codigo")
                for srec in lectura.get("sensores", []):
                    if srec.get("sensor") != sensor:
                        continue
                    try:
                        val = float(srec.get("valor"))
                    except Exception:
                        continue
                    # Truncar al bucket en Lima para alinear con dateTrunc
                    key_dt = to_lima(ts_dt)
                    # función auxiliar (existente en tu módulo) debería truncar según 'period' e 'interval'
                    key_dt = _truncate_dt(key_dt, period, (1 if interval == "auto" else int(interval)))
                    if per_node:
                        node_buckets.setdefault((nodo_code, key_dt), []).append(val)
                    else:
                        buckets.setdefault(key_dt, []).append(val)

        if per_node:
            series_map = {}
            for (nodo_code, key_dt), vals in node_buckets.items():
                pt = {"timestamp": key_dt.isoformat(), "value": (sum(vals) / len(vals) if vals else None)}
                series_map.setdefault(nodo_code, []).append(pt)
            series = [{"nodo": k, "points": sorted(v, key=lambda x: x["timestamp"])} for k, v in series_map.items()]
            meta = {
                "parcela_id": parcela_id,
                "parametro": sensor,
                "start": (start_utc.isoformat() if start_utc else None),
                "end": (end_utc.isoformat() if end_utc else None),
                "bucket": period,
                "tz": "America/Lima",
                "type": "per_node",
                "series_count": len(series)
            }
            return {"meta": meta, "series": series}

        points = [
            {"timestamp": k.isoformat(), "value": (sum(v) / len(v) if v else None)}
            for k, v in sorted(buckets.items())
        ]
        meta = {
            "parcela_id": parcela_id,
            "parametro": sensor,
            "start": (start_utc.isoformat() if start_utc else None),
            "end": (end_utc.isoformat() if end_utc else None),
            "bucket": period,
            "tz": "America/Lima",
            "points_count": len(points)
        }
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
    KPIs usando Ciclo activo (ya no etapa_actual en Parcela).
    - Admin/Superadmin: visión global.
    - Otros: visión filtrada por usuario.
    """
    from users.permissions import role_name
    r = role_name(user)

    def empty(scope='user'):
        return {
            "scope": scope,
            "total_parcelas": 0,
            "parcelas_con_ciclo_activo": 0,
            "parcelas_sin_ciclo_activo": 0,
            "avg_tamano_hectareas": None
        }

    if Parcela is None or Ciclo is None:
        return empty('global' if r in ('superadmin','administrador') else 'user')

    if r in ('superadmin', 'administrador'):
        total_parcelas = Parcela.objects.count()
        parcelas_con_ciclo_activo = Ciclo.objects.filter(estado='activo').values('parcela_id').distinct().count()
        parcelas_sin_ciclo_activo = total_parcelas - parcelas_con_ciclo_activo
        avg_tamano = Parcela.objects.aggregate(avg=Avg('tamano_hectareas'))['avg']
        reglas_activas = ReglaPorEtapa.objects.filter(activo=True).count() if ReglaPorEtapa else 0
        etapas_totales = Etapa.objects.count() if Etapa else 0
        parcelas_por_cultivo = list(
            Ciclo.objects.filter(estado='activo', cultivo__isnull=False)
            .values('cultivo__nombre').annotate(count=Count('parcela_id')).order_by('-count')
        )
        return {
            "scope": "global",
            "total_parcelas": total_parcelas,
            "parcelas_con_ciclo_activo": parcelas_con_ciclo_activo,
            "parcelas_sin_ciclo_activo": parcelas_sin_ciclo_activo,
            "avg_tamano_hectareas": float(avg_tamano) if avg_tamano is not None else None,
            "reglas_activas": reglas_activas,
            "etapas_totales": etapas_totales,
            "parcelas_por_cultivo": parcelas_por_cultivo,
        }

    # usuario (agricultor / técnico)
    qs_parcelas = Parcela.objects.filter(usuario=user)
    total_parcelas = qs_parcelas.count()
    ciclos_activos = Ciclo.objects.filter(parcela__usuario=user, estado='activo')
    parcelas_con_ciclo_activo = ciclos_activos.values('parcela_id').distinct().count()
    parcelas_sin_ciclo_activo = total_parcelas - parcelas_con_ciclo_activo
    avg_tamano = qs_parcelas.aggregate(avg=Avg('tamano_hectareas'))['avg']
    reglas_relevantes = ReglaPorEtapa.objects.filter(
        etapa__ciclos_en_etapa__in=ciclos_activos,
        activo=True
    ).distinct().count() if ReglaPorEtapa else 0
    etapas_distribution = list(
        ciclos_activos.values('etapa_actual__nombre')
        .annotate(count=Count('id')).order_by('-count')
    )
    parcelas_por_cultivo = list(
        ciclos_activos.filter(cultivo__isnull=False)
        .values('cultivo__nombre').annotate(count=Count('parcela_id')).order_by('-count')
    )
    return {
        "scope": "user",
        "total_parcelas": total_parcelas,
        "parcelas_con_ciclo_activo": parcelas_con_ciclo_activo,
        "parcelas_sin_ciclo_activo": parcelas_sin_ciclo_activo,
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

def _today_window_utc(now: datetime | None = None):
    """
    Retorna (start_utc, end_utc) del día actual en Lima convertidos a UTC.
    """
    now = now or timezone.now()
    lima_now = now.astimezone(LIMA_TZ)
    start_lima = lima_now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_lima = start_lima + timedelta(days=1)
    # pasar a UTC
    start_utc = start_lima.astimezone(UTC)
    end_utc = end_lima.astimezone(UTC)
    return start_utc, end_utc

def _score_linear(value: float | None, minimo: float | None, centro: float | None, maximo: float | None) -> float | None:
    """
    Score 0–100 con máximo en 'centro', baja lineal a 0 en 'minimo' y 'maximo'.
    - Si falta valor o reglas -> None
    - Fuera de [minimo, maximo] -> 0
    """
    if value is None or minimo is None or maximo is None or centro is None:
        return None
    try:
        v = float(value); mn = float(minimo); mx = float(maximo); c = float(centro)
    except Exception:
        return None
    if mn > mx:
        mn, mx = mx, mn
    if v < mn or v > mx:
        return 0.0
    # evitar divisiones por cero
    if c <= mn:
        # máximo pegado al mínimo: decae de mn(100) a mx(0)
        return max(0.0, 100.0 * (mx - v) / (mx - mn)) if mx > mn else 100.0
    if c >= mx:
        # máximo pegado al máximo: crece de mn(0) a mx(100)
        return max(0.0, 100.0 * (v - mn) / (mx - mn)) if mx > mn else 100.0
    if v == c:
        return 100.0
    if v < c:
        return max(0.0, 100.0 * (v - mn) / (c - mn))
    else:
        return max(0.0, 100.0 * (mx - v) / (mx - c))

SENSOR_ALIAS_MAP = {
    "temperatura": "Temperatura_aire",
    "humedad": "Humedad_suelo",
    "suelo": "Humedad_suelo",
    "ndvi": "Ndvi",
    "ph": "Ph",
    "radiacion": "Radiacion",
}

def _canonical_param(name: str) -> str:
    return SENSOR_ALIAS_MAP.get(name.lower(), name)

def _fetch_today_param_avgs(parcela_id: int, start_utc, end_utc) -> dict[str, float]:
    """
    Devuelve promedio por sensor del día actual: { sensor: avg_value }
    Promedia entre nodos y múltiples lecturas del día.
    """
    db = get_db()
    if db is None:
        return {}
    coll_name_candidates = ['lecturas_sensores', 'sensor_readings', 'readings']
    coll = None
    for n in coll_name_candidates:
        if n in db.list_collection_names():
            coll = db[n]
            break
    if coll is None:
        return {}

    pipeline = [
        {"$match": {
            "parcela_id": int(parcela_id),
            "timestamp": {"$gte": start_utc, "$lt": end_utc}
        }},
        {"$unwind": "$lecturas"},
        {"$unwind": "$lecturas.sensores"},
        {"$group": {
            "_id": "$lecturas.sensores.sensor",
            "avg_value": {"$avg": "$lecturas.sensores.valor"}
        }},
        {"$project": {"_id": 0, "sensor": "$_id", "value": "$avg_value"}}
    ]
    try:
        rows = list(coll.aggregate(pipeline, allowDiskUse=True))
    except Exception:
        # Fallback simple en caso de cluster limitado
        rows = []
        cursor = coll.find(
            {"parcela_id": int(parcela_id), "timestamp": {"$gte": start_utc, "$lt": end_utc}},
            projection=["lecturas"]
        )
        sums: dict[str, float] = {}
        counts: dict[str, int] = {}
        for d in cursor:
            for l in d.get("lecturas", []):
                for s in l.get("sensores", []):
                    name = s.get("sensor"); val = s.get("valor")
                    try:
                        fv = float(val)
                    except Exception:
                        continue
                    sums[name] = sums.get(name, 0.0) + fv
                    counts[name] = counts.get(name, 0) + 1
        for k, total in sums.items():
            rows.append({"sensor": k, "value": total / counts[k]})  # promedio

    raw = {r["sensor"]: float(r["value"]) for r in rows if r.get("sensor") and r.get("value") is not None}
    # normalizar nombres
    canon = {}
    for k, v in raw.items():
        canon_name = _canonical_param(k)
        canon.setdefault(canon_name, []).append(v)
    return {k: (sum(vals) / len(vals)) for k, vals in canon.items()}

def _latest_avgs_for_parcela(parcela_id: int) -> dict:
    """
    Promedia la última medición por nodo (por sensor) y devuelve:
    { "timestamp": ISO, "avgs": { sensor: promedio } }
    - Toma la última lectura por (nodo, sensor) y promedia entre nodos.
    - timestamp: del último documento usado en el cálculo.
    """
    db = get_db()
    if db is None:
        return {"timestamp": None, "avgs": {}}

    coll_name_candidates = ['lecturas_sensores', 'sensor_readings', 'readings']
    coll = None
    for n in coll_name_candidates:
        if n in db.list_collection_names():
            coll = db[n]
            break
    if coll is None:
        return {"timestamp": None, "avgs": {}}

    pipeline = [
        {"$match": {"parcela_id": int(parcela_id)}},
        {"$sort": {"timestamp": -1}},  # ordena documentos por timestamp desc
        {"$unwind": "$lecturas"},
        {"$unwind": "$lecturas.sensores"},
        {
            "$project": {
                "nodo": "$lecturas.nodo_codigo",
                "sensor": "$lecturas.sensores.sensor",
                "value": "$lecturas.sensores.valor",
                "timestamp": {
                    "$cond": [
                        {"$eq": [{"$type": "$timestamp"}, "date"]},
                        "$timestamp",
                        {"$dateFromString": {"dateString": "$timestamp"}}
                    ]
                }
            }
        },
        # agrupamos por (nodo, sensor) y tomamos la primera por el sort previo → última lectura
        {
            "$group": {
                "_id": {"nodo": "$nodo", "sensor": "$sensor"},
                "last_value": {"$first": "$value"},
                "last_ts": {"$first": "$timestamp"}
            }
        }
    ]

    rows = list(coll.aggregate(pipeline, allowDiskUse=True))
    by_sensor: dict[str, list[float]] = {}
    last_ts = None

    for r in rows:
        sensor = r["_id"]["sensor"]
        val = r.get("last_value")
        ts = r.get("last_ts")
        try:
            fv = float(val)
        except Exception:
            continue
        by_sensor.setdefault(sensor, []).append(fv)
        if ts and (last_ts is None or ts > last_ts):
            last_ts = ts

    avgs = { _canonical_param(k): (sum(v) / len(v) if v else None) for k, v in by_sensor.items() }
    ts_iso = (last_ts.isoformat() if last_ts else None)
    return {"timestamp": ts_iso, "avgs": avgs}

def compute_daily_kpis_parcela(parcela_id: int) -> dict:
    """
    KPIs diarios por parcela usando su Ciclo activo.
    """
    now = timezone.now()
    start_utc, end_utc = _today_window_utc(now)

    reglas_map: dict[str, dict] = {}
    ciclo = None
    if Ciclo:
        ciclo = (Ciclo.objects
                 .filter(parcela_id=parcela_id, estado='activo')
                 .select_related('etapa_actual')
                 .order_by('-created_at')
                 .first())

    if ciclo and ReglaPorEtapa:
        qs_reglas = ReglaPorEtapa.objects.filter(activo=True)
        if ciclo.etapa_actual:
            qs_reglas = qs_reglas.filter(etapa=ciclo.etapa_actual)
        else:
            qs_reglas = qs_reglas.none()
        for r in qs_reglas:
            param = r.parametro
            if not param:
                continue
            mn, mx = r.minimo, r.maximo
            centro = getattr(r, 'centro', None)
            if centro is None and mn is not None and mx is not None:
                try:
                    centro = (float(mn) + float(mx)) / 2.0
                except Exception:
                    centro = None
            reglas_map[param] = {
                "minimo": mn,
                "maximo": mx,
                "centro": centro,
                "nombre": str(param).capitalize()
            }

    avgs = _fetch_today_param_avgs(int(parcela_id), start_utc, end_utc)

    # Fallback: si no hay datos hoy, intentar últimas 24h (opcional)
    if not avgs:
        last24_start = (timezone.now() - timedelta(hours=24)).astimezone(UTC)
        last24_end = timezone.now().astimezone(UTC)
        avgs = _fetch_today_param_avgs(int(parcela_id), last24_start, last24_end)

    # reglas_map keys ya están con nombre de regla; asegurar inclusión de todas las reglas
    sensores = sorted(set(reglas_map.keys()) | set(avgs.keys()))

    kpis = []
    for s in sensores:
        avg_val = avgs.get(s)
        regla = reglas_map.get(s)
        if regla:
            score = _score_linear(avg_val, regla.get("minimo"), regla.get("centro"), regla.get("maximo"))
        else:
            score = 100.0 if avg_val is not None else None
        kpis.append({
            "nombre": s,
            "dato": (round(score) if score is not None else None)
        })

    # NUEVO: adjuntar últimos promedios (entre nodos) y timestamp de cálculo
    latest = _latest_avgs_for_parcela(int(parcela_id))

    return {
        "parcela_id": int(parcela_id),
        "fecha": now.astimezone(LIMA_TZ).date().isoformat(),
        "kpis": kpis,
        "last_avgs_timestamp": latest["timestamp"],
        "last_avgs": latest["avgs"]
    }

def compute_daily_kpis_for_user(user) -> dict:
    """
    Agrega KPIs diarios por parcela y promedio general (solo parcelas con Ciclo activo).
    """
    if Parcela is None:
        return {
            "usuario_id": getattr(user, 'id', None),
            "fecha": timezone.now().astimezone(LIMA_TZ).date().isoformat(),
            "parcelas": [],
            "general": []
        }

    parcela_ids = (Parcela.objects
                   .filter(usuario=user)
                   .values_list('id', flat=True))

    per_parcela = [compute_daily_kpis_parcela(pid) for pid in parcela_ids]

    # Conjunto completo de nombres (de reglas y de datos reales)
    all_names = set()
    for p in per_parcela:
        for k in p.get("kpis", []):
            all_names.add(k["nombre"])
    # incluir todas las reglas potenciales del usuario (si hay ciclos)
    if ReglaPorEtapa and Ciclo:
        ciclos_activos = Ciclo.objects.filter(parcela__usuario=user, estado='activo')
        reglas_user = ReglaPorEtapa.objects.filter(activo=True, etapa__in=[c.etapa_actual for c in ciclos_activos if c.etapa_actual])
        for r in reglas_user:
            if r.parametro:
                all_names.add(str(r.parametro))

    by_name: dict[str, list[float]] = {}
    for item in per_parcela:
        for k in item.get("kpis", []):
            val = k["dato"]
            if val is None:
                continue
            by_name.setdefault(k["nombre"], []).append(float(val))

    general = []
    for nombre in sorted(all_names):
        vals = by_name.get(nombre, [])
        general.append({
            "nombre": nombre,
            "dato": (round(sum(vals) / len(vals)) if vals else None)
        })

    return {
        "usuario_id": getattr(user, 'id', None),
        "fecha": timezone.now().astimezone(LIMA_TZ).date().isoformat(),
        "parcelas": per_parcela,
        "general": general
    }