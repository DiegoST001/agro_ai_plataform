from django.contrib import admin
from .models import Node, NodoSecundario, TokenNodo

@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'codigo', 'parcela', 'estado', 'bateria', 'senal', 'last_seen')
    search_fields = ('codigo',)
    list_filter = ('estado', 'parcela')

@admin.register(NodoSecundario)
class NodoSecundarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'codigo', 'maestro', 'estado', 'bateria', 'senal', 'last_seen')
    search_fields = ('codigo',)
    list_filter = ('estado',)

@admin.register(TokenNodo)
class TokenNodoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nodo', 'key', 'estado', 'fecha_creacion', 'fecha_expiracion')
    search_fields = ('key', 'nodo__codigo')
    list_filter = ('estado',)