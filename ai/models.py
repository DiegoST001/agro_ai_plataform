from django.db import models

class AIIntegration(models.Model):
    PROVIDER_CHOICES = [
        ('ollama', 'Ollama'),
        ('gemini', 'Gemini'),
        ('anthropic', 'Anthropic'),
        # Agrega más proveedores si lo necesitas
    ]
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    endpoint = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)
    nombre = models.CharField(max_length=50, default='', blank=True)

    def __str__(self):
        return f"{self.provider} ({'activo' if self.activo else 'inactivo'})"