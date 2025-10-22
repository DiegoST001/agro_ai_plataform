"""
Adapter para permisos del app 'nodes'. Reexporta la implementación central.
"""
from typing import Any
from users.permissions import (
    tiene_permiso as _tiene_permiso,
    role_name,
    HasOperationPermission,
    OwnsObjectOrAdmin,
)

def tiene_permiso(user: Any, modulo_nombre: str, operacion_nombre: str) -> bool:
    return _tiene_permiso(user, modulo_nombre, operacion_nombre)

__all__ = ['tiene_permiso', 'role_name', 'HasOperationPermission', 'OwnsObjectOrAdmin']