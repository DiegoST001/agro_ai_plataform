from django.db import models
from nodes.models import Node
from parcels.models import Parcela

class Sensor(models.Model):
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='sensors')
    parcela = models.ForeignKey(Parcela, on_delete=models.SET_NULL, null=True, blank=True, related_name='sensors')
    tipo = models.CharField(max_length=50)          # ej. soil_moisture, temp
    unidad = models.CharField(max_length=20)        # %, C, etc.
    ext_collection = models.CharField(max_length=100)  # colección en Mongo
    ext_sensor_id = models.CharField(max_length=100)   # id de sensor en Mongo
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo} sensor on {self.node} - {self.nombre}"