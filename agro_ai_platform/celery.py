import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agro_ai_platform.settings')
app = Celery('agro_ai_platform')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()