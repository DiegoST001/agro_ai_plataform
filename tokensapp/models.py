from django.db import models
from nodes.models import Node
import secrets

class NodeToken(models.Model):
    node = models.OneToOneField(Node, on_delete=models.CASCADE, related_name='token')
    key = models.CharField(max_length=64, unique=True, default=lambda: secrets.token_hex(32))
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)