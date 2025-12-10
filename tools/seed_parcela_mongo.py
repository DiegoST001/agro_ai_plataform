import os
import random
import argparse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from pymongo import MongoClient
from dotenv import load_dotenv

LIMA = ZoneInfo("America/Lima")
UTC = timezone.utc

# Sensores requeridos
SENSORES_DEF = [
    ("temperatura", "°C", (15.0, 35.0)),
    ("humedad_aire", "%", (30.0, 90.0)),
    ("humedad_suelo", "%", (10.0, 60.0)),
]

def rand_val(rango: tuple[float, float]) -> float:
    a, b = rango
    return round(random.uniform(a, b), 2)

def make_timestamp_utc(base_lima: datetime, offset_min: int) -> datetime:
    dt_local = base_lima + timedelta(minutes=offset_min)
    if dt_local.tzinfo is None:
        dt_local = dt_local.replace(tzinfo=LIMA)
    return dt_local.astimezone(UTC)

def pick_nodos_subset(nodos: list[str]) -> list[str]:
    """
    Devuelve:
      - a veces todos los nodos
      - a veces solo 1 nodo
      - a veces un subconjunto aleatorio
    """
    if not nodos:
        return []
    r = random.random()
    if r < 0.3:
        # solo 1
        return [random.choice(nodos)]
    elif r < 0.6:
        # subconjunto
        k = random.randint(1, len(nodos))
        return random.sample(nodos, k)
    else:
        # todos
        return list(nodos)

def build_doc(parcela_id: int, maestro_code: str, nodos_secundarios: list[str], ts_utc: datetime) -> dict:
    lecturas = []
    for nodo in pick_nodos_subset(nodos_secundarios):
        sensores = []
        # incluir entre 1 y 3 sensores de la lista requerida
        k = random.randint(1, len(SENSORES_DEF))
        for name, unit, rng in random.sample(SENSORES_DEF, k=k):
            sensores.append({
                "sensor": name,
                "valor": rand_val(rng),
                "unidad": unit,
            })
        # last_seen: a veces null, a veces cercano al timestamp
        last_seen = ts_utc - timedelta(minutes=random.randint(0, 15)) if random.random() < 0.75 else None

        lecturas.append({
            "nodo_codigo": nodo,
            "last_seen": last_seen,
            "sensores": sensores,
        })

    return {
        "seed_tag": "demo",
        "parcela_id": parcela_id,
        "codigo_nodo_maestro": maestro_code,
        "timestamp": ts_utc,
        "lecturas": lecturas,
    }

def _random_minutes_of_day(count: int) -> list[int]:
    count = max(1, min(int(count), 1440))
    # slots cada 5 min para evitar colisiones
    pool = list(range(0, 24 * 60, 5))
    k = min(count, len(pool))
    return sorted(random.sample(pool, k))

def _day_start_lima(d: datetime) -> datetime:
    return d.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=LIMA)

def main():
    parser = argparse.ArgumentParser(description="Seed de lecturas para una parcela específica en MongoDB.")
    parser.add_argument("--parcela-id", type=int, default=9, help="ID de la parcela (default: 9)")
    parser.add_argument("--maestro", type=str, default="M-400a1ab3-1", help="Código del nodo maestro")
    parser.add_argument("--nodos", type=str, default="NS-570bcc3c-1-M-400a1ab3-1,NS-e660f65a-2-M-400a1ab3-1", help="Lista de nodos secundarios separada por coma")
    parser.add_argument("--docs", type=int, default=64, help="Cantidad de documentos (modo antiguo, distribuido aleatorio)")
    parser.add_argument("--days", type=int, default=7, help="Días hacia atrás (incluye hoy)")
    parser.add_argument("--per-daycounts", type=str, default="", help="Conteos por día: '8,10,3' => hoy 8, ayer 10, anteayer 3")
    parser.add_argument("--min-per-day", type=int, default=3, help="Mínimo por día (modo aleatorio por día)")
    parser.add_argument("--max-per-day", type=int, default=15, help="Máximo por día (modo aleatorio por día)")
    parser.add_argument("--collection", type=str, default="", help="Nombre de colección destino")
    args = parser.parse_args()

    nodos_secundarios = [s.strip() for s in args.nodos.split(",") if s.strip()]

    load_dotenv()
    mongo_url = os.getenv("MONGO_URL")
    mongo_db = os.getenv("MONGO_DB", "sensors_db")
    if not mongo_url:
        raise RuntimeError("Configura MONGO_URL en tu .env")

    try:
        client = MongoClient(mongo_url, tz_aware=True, tzinfo=UTC, serverSelectionTimeoutMS=5000)
    except TypeError:
        client = MongoClient(mongo_url, tz_aware=True, serverSelectionTimeoutMS=5000)

    db = client[mongo_db]
    coll_name = args.collection or ("lecturas_sensores" if "lecturas_sensores" in db.list_collection_names() else "readings")
    coll = db[coll_name]

    now_lima = datetime.now(LIMA)
    docs = []

    if args.per_daycounts.strip():
        # Plan explícito por día: "8,10,3" => [hoy, ayer, anteayer]
        counts = [int(c) for c in args.per_daycounts.split(",") if c.strip()]
        for idx, cnt in enumerate(counts):
            day_dt = _day_start_lima(now_lima - timedelta(days=idx))
            for m in _random_minutes_of_day(cnt):
                ts_utc = (day_dt + timedelta(minutes=m)).astimezone(UTC)
                docs.append(build_doc(args.parcela_id, args.maestro, nodos_secundarios, ts_utc))
    else:
        # Aleatorio por día en los últimos --days (incluye hoy)
        for d in range(args.days + 1):
            cnt = random.randint(args.min_per_day, args.max_per_day)
            day_dt = _day_start_lima(now_lima - timedelta(days=d))
            for m in _random_minutes_of_day(cnt):
                ts_utc = (day_dt + timedelta(minutes=m)).astimezone(UTC)
                docs.append(build_doc(args.parcela_id, args.maestro, nodos_secundarios, ts_utc))
        # Si también se indicó --docs, hacemos un adicional distribuido como antes
        for i in range(max(0, args.docs - len(docs))):
            base = now_lima - timedelta(days=args.days)
            offset_minutes = (i * random.randint(30, 180)) % (args.days * 24 * 60)
            ts_utc = make_timestamp_utc(base, offset_minutes)
            docs.append(build_doc(args.parcela_id, args.maestro, nodos_secundarios, ts_utc))

    if docs:
        result = coll.insert_many(docs)
        print(f"Insertados {len(result.inserted_ids)} documentos en '{mongo_db}.{coll_name}' para parcela_id={args.parcela_id}")
    else:
        print("No se generaron documentos.")

if __name__ == "__main__":
    main()