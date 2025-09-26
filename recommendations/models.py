from django.db import models

class Recommendation(models.Model):
    # Choices declarados en el propio modelo
    TIPO_CHOICES = [
        ('general', 'General'),
        ('riego', 'Riego'),
        ('fertilizacion', 'Fertilización'),
        ('plaga', 'Control de plagas'),
        ('cosecha', 'Cosecha'),
    ]
    ESTADO_CHOICES = [
        ('nuevo', 'Nuevo'),
        ('en_progreso', 'En progreso'),
        ('completado', 'Completado'),
        ('descartado', 'Descartado'),
    ]

    # Evita import cruzado: usa referencia por string
    parcela = models.ForeignKey('parcels.Parcela', on_delete=models.CASCADE, related_name='recommendations')

    titulo = models.CharField(max_length=120)
    detalle = models.TextField()
    score = models.FloatField(default=0)
    source = models.CharField(max_length=50, default='rule')

    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES, default='general')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='nuevo')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Campos opcionales para workflow
    fecha_implementacion = models.DateTimeField(null=True, blank=True)
    resultado = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.titulo} - {self.estado}"

class TaskItem(models.Model):
    recommendation = models.ForeignKey(
        'recommendations.Recommendation',  # referencia por string, sin import directo
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='task_items',
    )
    created_at = models.DateTimeField(auto_now_add=True)