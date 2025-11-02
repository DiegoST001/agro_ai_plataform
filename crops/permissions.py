"""
Adapter para permisos del app 'crops'. Reexporta la implementación central
de users.permissions para mantener un punto único de control (caching/resolución).
"""
from functools import lru_cache
from typing import Any, Tuple, Optional

from users.models import Modulo, Operacion  # importados para resolución de ids si se necesita
from users.permissions import (
    tiene_permiso as _tiene_permiso,
    role_name,
    HasOperationPermission,
    OwnsObjectOrAdmin,
)

__all__ = ['tiene_permiso', 'role_name', 'HasOperationPermission', 'OwnsObjectOrAdmin']

@lru_cache(maxsize=256)
def _resolve_ids(modulo_nombre: str, operacion_nombre: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Resolve y cachea ids de Modulo y Operacion por nombre.
    Se expone por compatibilidad con el patrón usado en otras apps.
    """
    try:
        modulo = Modulo.objects.only('id').get(nombre=modulo_nombre)
        operacion = Operacion.objects.only('id').get(modulo=modulo, nombre=operacion_nombre)
        return modulo.id, operacion.id
    except (Modulo.DoesNotExist, Operacion.DoesNotExist):
        return None, None

def tiene_permiso(user: Any, modulo_nombre: str, operacion_nombre: str) -> bool:
    """
    Wrapper ligero que delega en la implementación central en users.permissions.
    Mantener este adapter facilita cambiar comportamiento local más adelante si es necesario.
    """
    return _tiene_permiso(user, modulo_nombre, operacion_nombre)