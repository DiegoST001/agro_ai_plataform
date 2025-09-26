from django.test import TestCase
from .models import UserProfile, Role

class UserProfileModelTest(TestCase):
    def setUp(self):
        self.role = Role.objects.create(nombre='agricultor', descripcion='Agricultural user')
        self.user_profile = UserProfile.objects.create(
            usuario_id=1,
            nombres='Diego',
            apellidos='Sanchez',
            telefono='123456789',
            dni='12345678',
            fecha_nacimiento='1990-01-01',
            experiencia_agricola=5,
            foto_perfil='path/to/photo.jpg'
        )

    def test_user_profile_creation(self):
        self.assertEqual(self.user_profile.nombres, 'Diego')
        self.assertEqual(self.user_profile.apellidos, 'Sanchez')
        self.assertEqual(self.user_profile.telefono, '123456789')
        self.assertEqual(self.user_profile.dni, '12345678')
        self.assertEqual(self.user_profile.experiencia_agricola, 5)

    def test_role_association(self):
        self.user_profile.rol = self.role
        self.user_profile.save()
        self.assertEqual(self.user_profile.rol.nombre, 'agricultor')

class RoleModelTest(TestCase):
    def setUp(self):
        self.role = Role.objects.create(nombre='administrador', descripcion='Administrator user')

    def test_role_creation(self):
        self.assertEqual(self.role.nombre, 'administrador')
        self.assertEqual(self.role.descripcion, 'Administrator user')