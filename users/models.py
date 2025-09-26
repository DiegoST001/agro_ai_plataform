from django.conf import settings
from django.db import models

class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nombres = models.CharField(max_length=50, blank=True, null=True)
    apellidos = models.CharField(max_length=50, blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    dni = models.CharField(max_length=8, blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    experiencia_agricola = models.IntegerField(blank=True, null=True)
    # foto_perfil = models.ImageField(upload_to='fotos_perfil/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

class Modulo(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

class Operacion(models.Model):
    modulo = models.ForeignKey('users.Modulo', on_delete=models.CASCADE, related_name='operaciones')
    nombre = models.CharField(max_length=50)  # sin unique=True

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['modulo', 'nombre'], name='unique_operacion_por_modulo')
        ]

    def __str__(self):
        return f'{self.modulo_id}:{self.nombre}'


class RolesOperaciones(models.Model):
    rol = models.ForeignKey('users.Rol', on_delete=models.CASCADE, related_name='permisos')
    modulo = models.ForeignKey('users.Modulo', on_delete=models.CASCADE, related_name='permisos')
    operacion = models.ForeignKey('users.Operacion', on_delete=models.CASCADE, related_name='permisos')

    created_at = models.DateTimeField(auto_now_add=True)  # 👈 agregado
    updated_at = models.DateTimeField(auto_now=True)      # 👈 agregado

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['rol', 'modulo', 'operacion'], name='unique_permiso')
        ]

class UserOperacionOverride(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='permisos_overrides')
    modulo = models.ForeignKey('users.Modulo', on_delete=models.CASCADE, related_name='user_overrides')
    operacion = models.ForeignKey('users.Operacion', on_delete=models.CASCADE, related_name='user_overrides')
    allow = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'modulo', 'operacion'], name='unique_user_override')
        ]

    def __str__(self):
        return f'{self.user_id}:{self.modulo_id}:{self.operacion_id} -> {"ALLOW" if self.allow else "DENY"}'
