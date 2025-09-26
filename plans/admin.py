from django.contrib import admin
from .models import Plan, ParcelaPlan

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'precio', 'frecuencia_minutos', 'created_at')
    search_fields = ('nombre',)

@admin.register(ParcelaPlan)
class ParcelaPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'parcela', 'plan', 'estado', 'fecha_inicio', 'fecha_fin')
    list_filter = ('estado', 'plan')
