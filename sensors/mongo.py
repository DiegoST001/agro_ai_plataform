from datetime import datetime
from django.conf import settings
from pymongo import MongoClient

_client = None
def get_client():
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URL)
    return _client

def readings_collection(name):
    return get_client()[settings.MONGO_DB][name]

def last_reading(collection: str, sensor_id: str):
    doc = readings_collection(collection).find_one({'sensor_id': sensor_id}, sort=[('ts', -1)])
    return doc

def range_readings(collection: str, sensor_id: str, start: datetime, end: datetime, limit: int = 1000):
    cursor = readings_collection(collection).find(
        {'sensor_id': sensor_id, 'ts': {'$gte': start, '$lte': end}}
    ).sort('ts', 1).limit(limit)
    return list(cursor)