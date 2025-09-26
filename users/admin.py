from django.contrib import admin
from .models import Rol, Modulo, Operacion, RolesOperaciones, PerfilUsuario, UserOperacionOverride

admin.site.register(Rol)
admin.site.register(Modulo)
admin.site.register(Operacion)
admin.site.register(RolesOperaciones)
admin.site.register(PerfilUsuario)
admin.site.register(UserOperacionOverride)