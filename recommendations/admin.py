from django.contrib import admin
from .models import Recommendation

@admin.register(Recommendation)
class RecomendacionesAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'titulo', 'created_at', 'estado', 'parcela')
    search_fields = ('tipo', 'titulo', 'detalle', 'estado')
    list_filter = ('tipo', 'estado')
    ordering = ('-created_at',)