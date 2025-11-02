from django.db import models
from django.conf import settings
# from django.utils import timezone
# from datetime import timedelta

class Cultivo(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'parcels_cultivo'  # reutiliza la tabla existente para evitar pérdida de datos

class Variedad(models.Model):
    cultivo = models.ForeignKey('crops.Cultivo', on_delete=models.CASCADE, related_name='variedades')
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('cultivo', 'nombre')
        db_table = 'parcels_variedad'

    def __str__(self):
        return f"{self.nombre} ({self.cultivo.nombre})"

class Etapa(models.Model):
    variedad = models.ForeignKey('crops.Variedad', on_delete=models.CASCADE, related_name='etapas')
    nombre = models.CharField(max_length=50)
    orden = models.PositiveIntegerField(default=1)
    descripcion = models.TextField(blank=True, null=True)
    duracion_estimada_dias = models.PositiveIntegerField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('variedad', 'nombre')
        ordering = ['orden']
        db_table = 'parcels_etapa'

    def __str__(self):
        return f"{self.nombre} - {self.variedad.nombre}"

class ReglaPorEtapa(models.Model):
    etapa = models.ForeignKey('crops.Etapa', on_delete=models.CASCADE, related_name='reglas')
    parametro = models.CharField(max_length=100)
    minimo = models.FloatField(null=True, blank=True)
    maximo = models.FloatField(null=True, blank=True)
    accion_si_menor = models.TextField(blank=True, null=True)
    accion_si_mayor = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    prioridad = models.IntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-prioridad', 'id']
        db_table = 'parcels_reglaporetapa'

    def __str__(self):
        return f"Regla {self.parametro} [{self.etapa.nombre}] (activo={self.activo})"
