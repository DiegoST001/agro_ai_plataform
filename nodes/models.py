from django.conf import settings
from django.db import models

ESTADO_CHOICES = [('activo', 'Activo'), ('inactivo', 'Inactivo')]

class Node(models.Model):  # Nodo Maestro
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nodes')
    codigo = models.CharField(max_length=50, unique=True)
    parcela = models.ForeignKey('parcels.Parcela', on_delete=models.CASCADE, related_name='nodos_maestros')
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activo')
    bateria = models.IntegerField(null=True, blank=True)   # %
    senal = models.IntegerField(null=True, blank=True)     # barras/RSRP
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.codigo


class NodoSecundario(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    maestro = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='secundarios')
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activo')
    bateria = models.IntegerField(null=True, blank=True)
    senal = models.IntegerField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.codigo


class TokenNodo(models.Model):
    ESTADO_CHOICES = [('valido', 'Válido'), ('en_gracia', 'En gracia'), ('invalidado', 'Invalidado')]
    nodo = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='tokens')
    key = models.CharField(max_length=64, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='valido')

    class Meta:
        indexes = [models.Index(fields=['key'])]

    def __str__(self):
        return f'{self.nodo.codigo}::{self.key[:8]}'