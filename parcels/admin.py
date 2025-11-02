from django.contrib import admin
from .models import Parcela, Ciclo

class CicloInline(admin.TabularInline):
    model = Ciclo
    extra = 0
    fields = ('id', 'cultivo', 'variedad', 'etapa_actual', 'etapa_inicio', 'estado', 'fecha_cierre', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(Parcela)
class ParcelaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nombre',
        'usuario',
        'tamano_hectareas',
        'ubicacion',
    )
    search_fields = (
        'nombre',
        'usuario__username',
    )
    list_filter = (
        'usuario',
    )
    ordering = ('id',)
    inlines = [CicloInline]

@admin.register(Ciclo)
class CicloAdmin(admin.ModelAdmin):
    list_display = ('id', 'parcela', 'cultivo', 'variedad', 'etapa_actual', 'estado', 'etapa_inicio', 'fecha_cierre')
    list_filter = ('estado', 'cultivo', 'variedad')
    search_fields = ('parcela__nombre',)
