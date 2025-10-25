from django.contrib import admin
from .models import Cultivo, Variedad, Etapa, ReglaPorEtapa, Parcela

@admin.register(Parcela)
class ParcelaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nombre',
        'usuario',
        'cultivo',
        'variedad',
        'tamano_hectareas',
        'ubicacion',
    )
    search_fields = (
        'nombre',
        'cultivo__nombre',
        'variedad__nombre',
        'usuario__username',
    )
    list_filter = (
        'cultivo',
        'variedad',
        'usuario',
    )
    ordering = ('id',)

@admin.register(Etapa)
class EtapaAdmin(admin.ModelAdmin):
    list_display = ('id','nombre','variedad','orden','duracion_estimada_dias')

@admin.register(ReglaPorEtapa)
class ReglaPorEtapaAdmin(admin.ModelAdmin):
    list_display = ('id','parametro','etapa','minimo','maximo','activo','prioridad','created_by','created_at')
    list_filter = ('activo','parametro','etapa__variedad__cultivo')
    search_fields = ('parametro','accion_si_mayor','accion_si_menor')
