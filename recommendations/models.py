from django.db import models
import uuid

class Recommendation(models.Model):
    TIPO_CHOICES = [
        ('general', 'General'),
        ('riego', 'Riego'),
        ('fertilizacion', 'Fertilización'),
        ('plaga', 'Control de plagas'),
        ('cosecha', 'Cosecha'),
        ('alerta', 'Alerta'),
    ]
    SEVERITY_CHOICES = [('info','Info'),('low','Baja'),('medium','Media'),('high','Alta'),('critical','Crítica')]
    STATUS_CHOICES = [('new','Nueva'),('read','Leída'),('archived','Archivada')]

    parcela = models.ForeignKey('parcels.Parcela', on_delete=models.CASCADE, related_name='recommendations')
    titulo = models.CharField(max_length=120)
    detalle = models.TextField()
    score = models.FloatField(default=0)
    source = models.CharField(max_length=50, default='rule')
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES, default='alerta')

    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='info')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='new')
    code = models.CharField(max_length=100, default='', blank=True)
    entity_type = models.CharField(max_length=50, default='', blank=True)
    entity_ref = models.CharField(max_length=100, default='', blank=True)
    meta = models.JSONField(default=dict, blank=True)
    fingerprint = models.CharField(max_length=32, unique=True, editable=False)
    expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['parcela','created_at']),
            models.Index(fields=['code']),
            models.Index(fields=['status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.titulo} - {self.tipo}"

    def save(self, *args, **kwargs):
        if not self.fingerprint:
            self.fingerprint = uuid.uuid4().hex
        super().save(*args, **kwargs)
