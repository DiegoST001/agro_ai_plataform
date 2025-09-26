from typing import Optional, Tuple
from datetime import datetime, timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from .models import TokenNodo

class NodeTokenAuthentication(BaseAuthentication):
    keyword = 'Node'

    def authenticate(self, request) -> Optional[Tuple[object, TokenNodo]]:
        auth = request.headers.get('Authorization') or ''
        token = None
        if auth.startswith(self.keyword + ' '):
            token = auth[len(self.keyword) + 1:].strip()
        if not token:
            token = request.headers.get('X-Node-Token')

        if not token:
            return None  # sin credenciales; DRF seguirá con otros authenticators

        t = TokenNodo.objects.select_related('nodo').filter(key=token).first()
        if not t or t.estado == 'invalidado':
            raise exceptions.AuthenticationFailed('Token de nodo inválido.')
        if t.fecha_expiracion and datetime.now(timezone.utc) > t.fecha_expiracion:
            raise exceptions.AuthenticationFailed('Token de nodo expirado.')

        # No autenticamos un usuario; marcamos el token como auth y colgamos el nodo en request
        request.node = t.nodo
        return (None, t)
