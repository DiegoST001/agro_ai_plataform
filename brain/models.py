from django.db import models
from django.conf import settings

EVENT_CHOICES = [
    ('login', 'Login'),
    ('consulta', 'Consulta'),
    ('actividad', 'Actividad'),
    ('alerta', 'Alerta'),
    ('cambio', 'Cambio'),
]

class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    event = models.CharField(max_length=32, choices=EVENT_CHOICES)
    module = models.CharField(max_length=64, blank=True, null=True)
    action = models.CharField(max_length=64, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['event', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]