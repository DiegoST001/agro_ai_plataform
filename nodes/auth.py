from typing import Optional, Tuple
from datetime import datetime, timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from .models import TokenNodo

class NodeTokenAuthentication(BaseAuthentication):
    """
    Acepta:
      - Authorization: Node <KEY>
      - Authorization: Token <KEY>   (compatibilidad)
      - X-Node-Token: <KEY>
    Al autenticar deja request.node = token.nodo y devuelve (token.nodo, token).
    """
    def authenticate(self, request) -> Optional[Tuple[object, TokenNodo]]:
        auth = get_authorization_header(request).split()
        key = None

        if auth and len(auth) >= 2:
            scheme = auth[0].decode('utf-8').lower()
            possible_key = auth[1].decode('utf-8')
            if scheme in ('node', 'token', 'bearer'):
                key = possible_key

        # fallback a header personalizado
        if not key:
            key = request.headers.get('X-Node-Token') or request.META.get('HTTP_X_NODE_TOKEN')

        if not key:
            return None  # no intenta autenticar

        try:
            token = TokenNodo.objects.select_related('nodo').get(key=key)
        except TokenNodo.DoesNotExist:
            raise AuthenticationFailed('Token de nodo inválido')

        # estado / expiración
        if token.estado == 'invalidado':
            raise AuthenticationFailed('Token invalidado')
        if token.fecha_expiracion and token.fecha_expiracion < timezone.now():
            # permitir 'en_gracia' si lo defines, aquí lo denegamos si expiró
            if token.estado != 'en_gracia':
                raise AuthenticationFailed('Token de nodo expirado')

        # attach node for handlers
        request.node = getattr(token, 'nodo', None)
        return (token.nodo, token)
