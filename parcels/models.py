from django.db import models
from django.conf import settings


class Cultivo(models.Model):
    nombre = models.CharField(max_length=50, unique=True)  # ej: "Palta", "Papaya"
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class Variedad(models.Model):
    cultivo = models.ForeignKey(Cultivo, on_delete=models.CASCADE, related_name='variedades')
    nombre = models.CharField(max_length=50)  # ej: "Hass", "Red Lady"
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('cultivo', 'nombre')

    def __str__(self):
        return f"{self.nombre} ({self.cultivo.nombre})"


class Etapa(models.Model):
    variedad = models.ForeignKey(Variedad, on_delete=models.CASCADE, related_name='etapas')
    nombre = models.CharField(max_length=50)
    orden = models.PositiveIntegerField(default=1)
    descripcion = models.TextField(blank=True, null=True)

    # optional: duración estimada en días para cálculo automático de siguiente etapa
    duracion_estimada_dias = models.PositiveIntegerField(null=True, blank=True)

    # nuevo: marcar si la etapa está disponible/activa globalmente
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('variedad', 'nombre')
        ordering = ['orden']

    def __str__(self):
        return f"{self.nombre} - {self.variedad.nombre}"


class ReglaPorEtapa(models.Model):
    """
    Reglas técnicas por etapa/variedad. Motor 'cerebro' las consumirá para evaluar umbrales.
    """
    etapa = models.ForeignKey(Etapa, on_delete=models.CASCADE, related_name='reglas')
    parametro = models.CharField(max_length=100)   # ej: 'temperatura_aire', 'humedad_suelo'
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

    def __str__(self):
        return f"Regla {self.parametro} [{self.etapa.nombre}] (activo={self.activo})"


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

    cultivo = models.ForeignKey(Cultivo, on_delete=models.SET_NULL, null=True, blank=True)
    variedad = models.ForeignKey(Variedad, on_delete=models.SET_NULL, null=True, blank=True)

    etapa_actual = models.ForeignKey(Etapa, on_delete=models.SET_NULL, null=True, blank=True, related_name='parcelas_en_etapa')
    etapa_inicio = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.nombre} ({self.usuario_id})'
