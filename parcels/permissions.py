"""
Adapter para permisos del app 'parcels'. Reexporta la implementación central
de users.permissions para evitar duplicación y mantener un punto único
de control para caching/resolución de ids.
"""
from functools import lru_cache
from django.contrib.auth.models import AnonymousUser
from users.models import RolesOperaciones, UserOperacionOverride, Modulo, Operacion
from users.permissions import (
    tiene_permiso as _tiene_permiso,
    role_name,
    HasOperationPermission,
    OwnsObjectOrAdmin,
)

__all__ = ['tiene_permiso', 'role_name', 'HasOperationPermission', 'OwnsObjectOrAdmin']

@lru_cache(maxsize=256)
def _resolve_ids(modulo_nombre: str, accion_nombre: str) -> tuple[int | None, int | None]:
    try:
        modulo = Modulo.objects.only('id').get(nombre=modulo_nombre)
        operacion = Operacion.objects.only('id').get(modulo=modulo, nombre=accion_nombre)
        return modulo.id, operacion.id
    except (Modulo.DoesNotExist, Operacion.DoesNotExist):
        return None, None

def tiene_permiso(user: Any, modulo_nombre: str, accion_nombre: str) -> bool:
    return _tiene_permiso(user, modulo_nombre, accion_nombre)