from django.contrib import admin
from .models import Parcela

@admin.register(Parcela)
class ParcelaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'usuario', 'tamano_hectareas', 'ubicacion')
    search_fields = ('nombre', 'tipo_cultivo')
    list_filter = ('tipo_cultivo', 'usuario_id')
    ordering = ('id',)