import os
from typing import Optional
from pymongo import MongoClient
from django.conf import settings

_client: Optional[MongoClient] = None
_db = None

def _mongo_settings():
    mongo_url = getattr(settings, "MONGO_URL", None) or os.getenv("MONGO_URL")
    mongo_db = getattr(settings, "MONGO_DB", None) or os.getenv("MONGO_DB")
    if not mongo_url or not mongo_db:
        raise RuntimeError("MONGO_URL y MONGO_DB deben estar definidos")
    return mongo_url, mongo_db

def get_client(serverSelectionTimeoutMS: int = 5000, **kwargs):
    global _client
    if _client is None:
        mongo_url, _ = _mongo_settings()
        _client = MongoClient(mongo_url, serverSelectionTimeoutMS=serverSelectionTimeoutMS, **kwargs)
    return _client

def get_db():
    global _db
    if _db is None:
        client = get_client()
        _, mongo_db = _mongo_settings()
        _db = client[mongo_db]
    return _db