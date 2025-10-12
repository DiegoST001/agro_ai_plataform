from django.db import models

class Recommendation(models.Model):
    TIPO_CHOICES = [
        ('general', 'General'),
        ('riego', 'Riego'),
        ('fertilizacion', 'Fertilización'),
        ('plaga', 'Control de plagas'),
        ('cosecha', 'Cosecha'),
        ('alerta', 'Alerta'),
    ]

    parcela = models.ForeignKey('parcels.Parcela', on_delete=models.CASCADE, related_name='recommendations')
    titulo = models.CharField(max_length=120)
    detalle = models.TextField()
    score = models.FloatField(default=0)
    source = models.CharField(max_length=50, default='rule')
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES, default='general')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.titulo} - {self.tipo}"
