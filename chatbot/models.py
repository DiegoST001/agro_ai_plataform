from django.db import models
from django.utils import timezone


class ChatMessage(models.Model):
    """Modelo para guardar el historial de mensajes del chat"""
    username = models.CharField(max_length=150, help_text="Nombre del usuario que envió el mensaje")
    message = models.TextField(help_text="Contenido del mensaje")
    is_user = models.BooleanField(default=True, help_text="True si es mensaje del usuario, False si es del bot")
    timestamp = models.DateTimeField(default=timezone.now, help_text="Fecha y hora del mensaje")
    
    class Meta:
        ordering = ['timestamp']
        verbose_name = 'Mensaje de Chat'
        verbose_name_plural = 'Mensajes de Chat'
    
    def __str__(self):
        msg_type = "Usuario" if self.is_user else "Bot"
        return f"{msg_type} - {self.username} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class CropData(models.Model):
    """Modelo para datos simulados del cultivo de fresas"""
    temperature_air = models.FloatField(help_text="Temperatura del aire en °C")
    humidity_air = models.FloatField(help_text="Humedad del aire en %")
    humidity_soil = models.FloatField(help_text="Humedad del suelo en %")
    conductivity_ec = models.FloatField(help_text="Conductividad eléctrica en dS/m")
    temperature_soil = models.FloatField(help_text="Temperatura del suelo en °C")
    solar_radiation = models.FloatField(help_text="Radiación solar en W/m²")
    pest_risk = models.CharField(
        max_length=20,
        choices=[('Bajo', 'Bajo'), ('Moderado', 'Moderado'), ('Alto', 'Alto')],
        default='Bajo',
        help_text="Nivel de riesgo de plagas"
    )
    last_updated = models.DateTimeField(default=timezone.now, help_text="Última actualización de datos")
    
    class Meta:
        verbose_name = 'Datos de Cultivo'
        verbose_name_plural = 'Datos de Cultivo'
    
    def __str__(self):
        return f"Datos - {self.last_updated.strftime('%Y-%m-%d %H:%M')}"
