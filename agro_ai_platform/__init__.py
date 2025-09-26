try:
    from .celery import app as celery_app  # noqa
except Exception:
    celery_app = None  # Permite levantar Django sin Celery instalado