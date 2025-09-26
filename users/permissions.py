from rest_framework.permissions import BasePermission
from .models import RolesOperaciones, Modulo, Operacion, UserOperacionOverride

class HasOperationPermission(BasePermission):
    """
    Permiso por rol/módulo/operación con overrides por usuario.
    Ejemplo: HasOperationPermission('parcelas', 'ver')
    """
    def __init__(self, modulo_nombre: str, operacion_nombre: str):
        self.modulo_nombre = modulo_nombre
        self.operacion_nombre = operacion_nombre

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False

        # superadmin: acceso total
        if getattr(user, 'rol', None) and getattr(user.rol, 'nombre', '').lower() == 'superadmin':
            return True

        try:
            modulo = Modulo.objects.get(nombre=self.modulo_nombre)
            operacion = Operacion.objects.get(modulo=modulo, nombre=self.operacion_nombre)
        except (Modulo.DoesNotExist, Operacion.DoesNotExist):
            return False

        # 1) override por usuario (si existe, manda)
        ov = UserOperacionOverride.objects.filter(user=user, modulo=modulo, operacion=operacion).first()
        if ov is not None:
            return ov.allow

        # 2) fallback: permiso por rol
        return RolesOperaciones.objects.filter(rol=user.rol, modulo=modulo, operacion=operacion).exists()