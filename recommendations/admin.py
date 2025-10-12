from django.contrib import admin
from .models import Recommendation

@admin.register(Recommendation)
class RecomendacionesAdmin(admin.ModelAdmin):
    list_display = ('id', 'parcela', 'titulo', 'tipo', 'score', 'created_at')  # elimina 'estado'
    search_fields = ('titulo', 'detalle')
    list_filter = ('tipo',)  # elimina 'estado'