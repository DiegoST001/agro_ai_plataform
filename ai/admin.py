from django.contrib import admin
from .models import AIIntegration

@admin.register(AIIntegration)
class AIIntegrationAdmin(admin.ModelAdmin):
    list_display = ("provider", "nombre", "activo", "endpoint")
    list_filter = ("provider", "activo")
    search_fields = ("nombre", "endpoint")