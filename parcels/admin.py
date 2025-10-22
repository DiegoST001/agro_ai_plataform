from django.contrib import admin
from .models import Parcela

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
