from django.conf import settings
from django.db import models
from parcels.models import Parcela
from django.utils import timezone
from datetime import timedelta
import secrets

ESTADO_CHOICES = [('activo', 'Activo'), ('inactivo', 'Inactivo')]

class Node(models.Model):  # Nodo Maestro
    codigo = models.CharField(max_length=50, unique=True, blank=True)
    parcela = models.ForeignKey(Parcela, on_delete=models.CASCADE, related_name='nodos_maestros')
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='inactivo')
    bateria = models.IntegerField(null=True, blank=True)   # % batería del maestro
    senal = models.IntegerField(null=True, blank=True)     # Intensidad de señal 2G
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.codigo

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.codigo:
            token = secrets.token_hex(4)
            self.codigo = f"M-{token}-{self.id}"
            super().save(update_fields=['codigo'])

        # Crear token de nodo automático al crear el Node (si no existe)
        if creating:
            from django.db import IntegrityError
            try:
                # genera key larga y única
                key = secrets.token_hex(32)
                # TokenNodo está definido más abajo en el mismo archivo
                TokenNodo.objects.create(
                    nodo=self,
                    key=key,
                    fecha_expiracion=timezone.now() + timedelta(days=30),
                    estado='valido'
                )
            except IntegrityError:
                # en caso de colisión rara, omitir (o reintentar según necesidad)
                pass


class NodoSecundario(models.Model):
    codigo = models.CharField(max_length=50, unique=True, blank=True)
    maestro = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='secundarios')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='inactivo')
    bateria = models.IntegerField(null=True, blank=True)  # % batería del nodo secundario
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.codigo

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.codigo and self.maestro and self.maestro.codigo:
            token = secrets.token_hex(4)
            self.codigo = f"NS-{token}-{self.id}-{self.maestro.codigo}"
            super().save(update_fields=['codigo'])



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



