from django.db import models
from parcels.models import Parcela  # Assuming Parcel model is defined in parcels/models.py
from sensors.models import Sensor

class AlertRule(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='rules')
    operador = models.CharField(max_length=5, choices=[('>','>'),('<','<'),('>=','>='),('<=','<='),('==','==')])
    umbral = models.FloatField()
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Alert(models.Model):
    ALERT_TYPES = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]

    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    tipo = models.CharField(max_length=50, choices=ALERT_TYPES)
    severidad = models.CharField(max_length=50, choices=SEVERITY_LEVELS)
    mensaje = models.TextField()
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    fecha_lectura = models.DateTimeField(null=True, blank=True)
    parcela = models.ForeignKey(Parcela, on_delete=models.CASCADE, related_name='alertas')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='alerts')
    valor = models.FloatField()
    triggered_at = models.DateTimeField(auto_now_add=True)
    rule = models.ForeignKey(AlertRule, on_delete=models.SET_NULL, null=True, blank=True, related_name='alerts')

    def __str__(self):
        return f"{self.tipo} - {self.severidad} - {self.mensaje}"