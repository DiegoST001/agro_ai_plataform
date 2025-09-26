from django.core.management.base import BaseCommand
from django.conf import settings
from pymongo import MongoClient
from datetime import datetime, timedelta
import random

class Command(BaseCommand):
    help = 'Genera lecturas de prueba en Mongo'

    def handle(self, *args, **kwargs):
        cli = MongoClient(settings.MONGO_URL)
        db = cli[settings.MONGO_DB]
        coll = db['readings']  # ejemplo único
        coll.delete_many({'sensor_id': {'$in': ['S-1','S-2']}})
        base = datetime.utcnow() - timedelta(hours=2)
        for sid in ['S-1', 'S-2']:
            docs = []
            t = base
            for _ in range(240):
                docs.append({'sensor_id': sid, 'value': round(random.uniform(10, 90), 2), 'ts': t})
                t += timedelta(minutes=1)
            coll.insert_many(docs)
        self.stdout.write(self.style.SUCCESS('Mongo seeded'))