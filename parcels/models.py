from django.db import models
from django.conf import settings

# ...existing code...
# Eliminar el modelo Plan que estaba aquí (si existía).

class Parcela(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='parcelas')
    nombre = models.CharField(max_length=100)
    ubicacion = models.CharField(max_length=255, blank=True, default='')
    tamano_hectareas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    altitud = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    tipo_cultivo = models.CharField(max_length=50, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.nombre} ({self.usuario_id})'