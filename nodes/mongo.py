import os
from pymongo import MongoClient

mongo_url = os.getenv('MONGO_URL')
mongo_db = os.getenv('MONGO_DB')

client = MongoClient(mongo_url)
db = client[mongo_db]