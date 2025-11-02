from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

# Removed: Cultivo, Variedad, Etapa, ReglaPorEtapa moved to app `crops`
# -------------------------------------------------------------------
# Ahora `parcels` solo define Parcela y Ciclo; referencias a cultivo/variedad/etapa
# apuntan a 'crops.*' para reutilizar las tablas/modelos en la nueva app.
# -------------------------------------------------------------------

class Parcela(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='parcelas'
    )
    nombre = models.CharField(max_length=100)
    ubicacion = models.CharField(max_length=255, blank=True, default='')
    tamano_hectareas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    altitud = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # Nota: los modelos Cultivo/Variedad/Etapa/ReglaPorEtapa fueron movidos a la app 'crops'.
    # La información de cultivo/variedad/etapa ahora vive en el modelo Ciclo (histórico por campaña).

    etapa_inicio = models.DateField(null=True, blank=True)  # opcional
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.nombre} ({self.usuario_id})'


class Ciclo(models.Model):
    ESTADO_CHOICES = (
        ('activo', 'Activo'),
        ('cerrado', 'Cerrado'),
    )

    parcela = models.ForeignKey(Parcela, on_delete=models.CASCADE, related_name='ciclos')
    cultivo = models.ForeignKey('crops.Cultivo', on_delete=models.SET_NULL, null=True, blank=True)
    variedad = models.ForeignKey('crops.Variedad', on_delete=models.SET_NULL, null=True, blank=True)

    etapa_actual = models.ForeignKey('crops.Etapa', on_delete=models.SET_NULL, null=True, blank=True, related_name='ciclos_en_etapa')
    etapa_inicio = models.DateField(null=True, blank=True)

    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo')
    fecha_cierre = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Ciclo {self.pk} - {self.parcela.nombre} ({self.cultivo.nombre if self.cultivo else "sin cultivo"})'

    def is_active(self) -> bool:
        return self.estado == 'activo'

    def close(self, fecha=None):
        """Marca el ciclo como cerrado."""
        if self.estado == 'cerrado':
            return False
        self.estado = 'cerrado'
        self.fecha_cierre = fecha or timezone.now().date()
        self.save(update_fields=['estado', 'fecha_cierre', 'updated_at'])
        return True

    def advance_etapa_if_needed(self, now=None) -> bool:
        """
        Avanza a la siguiente etapa si la etapa_actual cumplió su duración_estimada_dias.
        Retorna True si se avanzó.
        """
        if not self.etapa_actual or not self.is_active():
            return False

        dur = getattr(self.etapa_actual, 'duracion_estimada_dias', None)
        if not dur:
            return False

        now = (now or timezone.now()).date()
        if not self.etapa_inicio:
            # inicializar etapa_inicio si no existe
            self.etapa_inicio = now
            self.save(update_fields=['etapa_inicio'])
            return False

        end_date = self.etapa_inicio + timedelta(days=int(dur))
        if now < end_date:
            return False

        # buscar siguiente etapa activa por orden (usando modelo Etapa desde crops)
        from django.apps import apps
        Etapa = apps.get_model('crops', 'Etapa')
        siguiente = Etapa.objects.filter(
            variedad=self.etapa_actual.variedad,
            orden__gt=self.etapa_actual.orden,
            activo=True
        ).order_by('orden').first()

        if not siguiente:
            return False

        self.etapa_actual = siguiente
        self.etapa_inicio = end_date
        self.save(update_fields=['etapa_actual', 'etapa_inicio', 'updated_at'])
        return True
