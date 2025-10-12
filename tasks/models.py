from django.db import models
from parcels.models import Parcela

class Task(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]

    parcela = models.ForeignKey(Parcela, on_delete=models.CASCADE)
    recomendacion = models.ForeignKey('recommendations.Recommendation', null=True, blank=True, on_delete=models.SET_NULL, related_name='tareas_asociadas')
    tipo = models.CharField(max_length=50)
    descripcion = models.TextField()
    fecha_programada = models.DateTimeField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    origen = models.CharField(max_length=20, choices=[('manual','Manual'),('ia','IA')], null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Tarea {self.tipo} para {self.parcela.nombre}"