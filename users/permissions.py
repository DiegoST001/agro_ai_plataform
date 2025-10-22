from functools import lru_cache
from rest_framework.permissions import BasePermission
from django.contrib.auth.models import AnonymousUser

from .models import RolesOperaciones, Modulo, Operacion, UserOperacionOverride

def role_name(user):
    return getattr(getattr(user, 'rol', None), 'nombre', None)

@lru_cache(maxsize=256)
def _resolve_ids(modulo_nombre: str, operacion_nombre: str) -> tuple[int | None, int | None]:
    try:
        modulo = Modulo.objects.only('id').get(nombre=modulo_nombre)
        operacion = Operacion.objects.only('id').get(modulo=modulo, nombre=operacion_nombre)
        return modulo.id, operacion.id
    except (Modulo.DoesNotExist, Operacion.DoesNotExist):
        return None, None

def tiene_permiso(user, modulo_nombre: str, operacion_nombre: str) -> bool:
    if isinstance(user, AnonymousUser) or not getattr(user, 'is_authenticated', False):
        return False

    # superadmin: acceso total
    if role_name(user) == 'superadmin':
        return True

    modulo_id, operacion_id = _resolve_ids(modulo_nombre, operacion_nombre)
    if not modulo_id or not operacion_id:
        return False

    # override por usuario (manda)
    ov = UserOperacionOverride.objects.filter(
        user=user, modulo_id=modulo_id, operacion_id=operacion_id
    ).first()
    if ov is not None:
        return ov.allow

    # permiso por rol
    rol = getattr(user, 'rol', None)
    if not rol:
        return False
    return RolesOperaciones.objects.filter(
        rol=rol, modulo_id=modulo_id, operacion_id=operacion_id
    ).exists()

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
        return tiene_permiso(user, self.modulo_nombre, self.operacion_nombre)

class OwnsObjectOrAdmin(BasePermission):
    # Admin/Superadmin pueden todo; otros deben ser dueños.
    # La vista puede definir owner_path (por defecto 'usuario'), admite relaciones con '__'.
    admin_roles = {'superadmin', 'administrador'}

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if role_name(request.user) in self.admin_roles:
            return True
        owner_path = getattr(view, 'owner_path', 'usuario').replace('__', '.')
        cur = obj
        for part in owner_path.split('.'):
            cur = getattr(cur, part, None)
            if cur is None:
                return False
        # comparar por PK (o por el valor si no existe .pk) para evitar falsos negativos
        owner_value = getattr(cur, 'pk', cur)
        user_value = getattr(request.user, 'pk', request.user)
        return owner_value == user_value