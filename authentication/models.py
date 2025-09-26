from django.contrib.auth.models import AbstractUser
from django.db import models
from users.models import Rol

class User(AbstractUser):
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, default=1)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.username

class TokenUsuario(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=255)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField()
    estado = models.CharField(max_length=50, choices=[
        ('activo', 'activo'),
        ('expirado', 'expirado'),
        ('invalidado', 'invalidado')
    ])

    def __str__(self):
        return f'Token for {self.usuario.username}'