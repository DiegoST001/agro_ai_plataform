from django.db import models

class SensorReading(models.Model):
    nodo_id = models.CharField(max_length=50)
    parcela_id = models.IntegerField()
    sensor_tipo = models.CharField(max_length=50)
    valor = models.FloatField()
    unidad = models.CharField(max_length=10)
    timestamp = models.DateTimeField()

    def __str__(self):
        return f"{self.sensor_tipo} reading from {self.nodo_id} at {self.timestamp}"

class AIRecommendation(models.Model):
    tipo = models.CharField(max_length=50)
    descripcion = models.TextField()
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    fecha_implementacion = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=[
        ('pendiente', 'Pendiente'),
        ('aceptada', 'Aceptada'),
        ('rechazada', 'Rechazada'),
    ])
    resultado = models.TextField(null=True, blank=True)
    parcela_id = models.IntegerField()

    def __str__(self):
        return f"Recommendation {self.tipo} for parcel {self.parcela_id}"