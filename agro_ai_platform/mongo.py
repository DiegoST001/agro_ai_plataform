import os
from typing import Optional
from pymongo import MongoClient
from django.conf import settings
from functools import lru_cache
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone as dj_tz
from django.utils.dateparse import parse_datetime

UTC = timezone.utc
LIMA_TZ = ZoneInfo("America/Lima")

_client: Optional[MongoClient] = None
_db = None


def _mongo_settings():
    """
    Devuelve los valores de configuración de MongoDB.
    Solo requiere MONGO_URL y MONGO_DB.
    """
    mongo_url = getattr(settings, "MONGO_URL", None) or os.getenv("MONGO_URL")
    mongo_db = getattr(settings, "MONGO_DB", None) or os.getenv("MONGO_DB")

    if not mongo_url:
        raise RuntimeError("Debes definir MONGO_URL en settings o .env")

    if not mongo_db:
        raise RuntimeError("Debes definir MONGO_DB en settings o .env")

    return mongo_url, mongo_db


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    if not settings.MONGO_URL:
        raise ImproperlyConfigured("MONGO_URL no configurado")
    try:
        # Preferir tzinfo=UTC cuando PyMongo lo soporta
        return MongoClient(
            settings.MONGO_URL,
            tz_aware=True,
            tzinfo=UTC,
            serverSelectionTimeoutMS=5000,
        )
    except TypeError:
        # Fallback para versiones sin soporte de tzinfo
        return MongoClient(
            settings.MONGO_URL,
            tz_aware=True,
            serverSelectionTimeoutMS=5000,
        )


def get_db():
    """
    Retorna la base de datos ya inicializada.
    """
    global _db
    if _db is None:
        client = get_client()
        _, mongo_db = _mongo_settings()
        _db = client[mongo_db]
    return _db


def now_utc() -> datetime:
    # Django ya entrega aware (UTC) cuando USE_TZ=True
    return dj_tz.now()


def to_utc(dt) -> datetime:
    """
    Convierte dt (str|datetime) a aware UTC.
    - Si es string ISO8601, lo parsea.
    - Si es naive, asume America/Lima y lo convierte a UTC.
    """
    if isinstance(dt, str):
        parsed = parse_datetime(dt)
        if parsed is None:
            raise ValueError(f"Fecha inválida: {dt}")
        dt = parsed
    if not isinstance(dt, datetime):
        raise ValueError("Se esperaba datetime o ISO8601 string")
    if dt.tzinfo is None:
        # asumir hora local de Perú si viene naive
        dt = dt.replace(tzinfo=LIMA_TZ)
    return dt.astimezone(UTC)


def to_lima(dt) -> datetime:
    """
    Convierte un datetime (str|datetime) a aware en America/Lima.
    Si es string, lo parsea primero.
    """
    if isinstance(dt, str):
        parsed = parse_datetime(dt)
        if parsed is None:
            raise ValueError(f"Fecha inválida: {dt}")
        dt = parsed
    if dt.tzinfo is None:
        # si viene naive asumimos UTC para evitar ambigüedad y pasamos a Lima
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(LIMA_TZ)
