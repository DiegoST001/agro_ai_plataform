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
from rest_framework.permissions import BasePermission
from .models import Node, NodoSecundario
from .permissions import role_name  # si ya existe en este módulo, ajusta el import

def tiene_permiso(user: Any, modulo_nombre: str, operacion_nombre: str) -> bool:
    return _tiene_permiso(user, modulo_nombre, operacion_nombre)

class OwnsNodeOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Admines ven todo
        if role_name(request.user) in ['superadmin', 'administrador']:
            return True
        # Dueño para Node
        if isinstance(obj, Node):
            return getattr(obj.parcela, 'usuario_id', None) == request.user.id
        # Dueño para NodoSecundario
        if isinstance(obj, NodoSecundario):
            maestro = getattr(obj, 'maestro', None)
            if maestro and getattr(maestro.parcela, 'usuario_id', None) == request.user.id:
                return True
        return False

__all__ = ['tiene_permiso', 'role_name', 'HasOperationPermission', 'OwnsObjectOrAdmin']