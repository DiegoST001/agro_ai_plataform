"""
Script para popular MongoDB con lecturas de sensores aleatorias.
- Usa variables de entorno: MONGO_URL, MONGO_DB
- Genera 100+ documentos para múltiples parcelas/nodos/sensores
- Timestamps en UTC, estructura compatible con tu API

Ejecutar en Windows (PowerShell):
  cd /d d:\CURSOS\Prueba\agro_ai_platform
  .\venv\Scripts\Activate.ps1
  python tools\populate_mongo.py
"""
import os
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from pymongo import MongoClient
from dotenv import load_dotenv

# Config
TOTAL_DOCS = 120  # cantidad de documentos (cada uno contiene lecturas de varios nodos)
PARCELAS = list(range(1, 8))  # 7 parcelas: 1..7
NODOS_POR_PARCELA = {
    # cada parcela tendrá estos nodos secundarios
    1: ["NODE-01-S1", "NODE-01-S2", "NODE-01-S3"],
    2: ["NODE-02-S1", "NODE-02-S2"],
    3: ["NODE-03-S1", "NODE-03-S2", "NODE-03-S3", "NODE-03-S4"],
    4: ["NODE-04-S1"],
    5: ["NODE-05-S1", "NODE-05-S2"],
    6: ["NODE-06-S1", "NODE-06-S2", "NODE-06-S3"],
    7: ["NODE-07-S1", "NODE-07-S2"],
}
MAESTROS = {p: f"NODE-{p:03d}" for p in PARCELAS}

SENSORES_DEF = [
    # nombre, unidad, rango (min, max)
    ("temperatura", "°C", (15.0, 35.0)),
    ("humedad", "%", (30.0, 90.0)),
    ("suelo", "%", (10.0, 60.0)),
    ("ph", "pH", (5.5, 8.5)),
]

LIMA = ZoneInfo("America/Lima")
UTC = timezone.utc


def rand_val(rango: tuple[float, float]) -> float:
    a, b = rango
    return round(random.uniform(a, b), 2)


def make_timestamp_utc(base_lima: datetime, offset_min: int) -> datetime:
    # base en Lima, aplicar offset y convertir a UTC
    dt_local = base_lima + timedelta(minutes=offset_min)
    if dt_local.tzinfo is None:
        dt_local = dt_local.replace(tzinfo=LIMA)
    return dt_local.astimezone(UTC)


def build_lectura(parcela_id: int, ts_utc: datetime) -> dict:
    lecturas = []
    for nodo in NODOS_POR_PARCELA.get(parcela_id, []):
        sensores = []
        # Genera 2-3 sensores por nodo
        for name, unit, rng in random.sample(SENSORES_DEF, k=random.randint(2, min(3, len(SENSORES_DEF)))):
            sensores.append({
                "sensor": name,
                "valor": rand_val(rng),
                "unidad": unit,
            })
        # Simular last_seen (a veces null, a veces cercano al timestamp)
        if random.random() < 0.75:
            last_seen = ts_utc - timedelta(minutes=random.randint(0, 15))
        else:
            last_seen = None

        lecturas.append({
            "nodo_codigo": nodo,
            "last_seen": last_seen,
            "sensores": sensores,
        })

    return {
        "seed_tag": "demo",
        "parcela_id": parcela_id,
        "codigo_nodo_maestro": MAESTROS[parcela_id],
        "timestamp": ts_utc,
        "lecturas": lecturas,
    }


def main():
    load_dotenv()
    mongo_url = os.getenv("MONGO_URL")
    mongo_db = os.getenv("MONGO_DB", "sensors_db")
    if not mongo_url:
        raise RuntimeError("Configura MONGO_URL en tu .env")

    # Compatibilidad: intentar tzinfo y hacer fallback si no se soporta
    try:
        client = MongoClient(mongo_url, tz_aware=True, tzinfo=UTC, serverSelectionTimeoutMS=5000)
    except TypeError:
        client = MongoClient(mongo_url, tz_aware=True, serverSelectionTimeoutMS=5000)

    db = client[mongo_db]

    # Seleccionar colección (preferencia por 'lecturas_sensores')
    coll_name = "lecturas_sensores" if "lecturas_sensores" in db.list_collection_names() else "readings"
    coll = db[coll_name]

    # Base temporal: últimos 7 días, ~16 docs por día
    now_lima = datetime.now(LIMA)
    base_start = now_lima - timedelta(days=7)

    docs = []
    for i in range(TOTAL_DOCS):
        parcela_id = random.choice(PARCELAS)
        # Distribuye timestamps: cada doc ~cada 60–180 min
        offset_minutes = (i * random.randint(60, 180)) % (7 * 24 * 60)
        ts_utc = make_timestamp_utc(base_start, offset_minutes)
        doc = build_lectura(parcela_id, ts_utc)
        docs.append(doc)

    # Insertar en batch
    if docs:
        result = coll.insert_many(docs)
        print(f"Insertados {len(result.inserted_ids)} documentos en '{mongo_db}.{coll_name}'")
    else:
        print("No se generaron documentos.")


if __name__ == "__main__":
    main()