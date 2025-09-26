from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Parcela

class ParcelaModelTest(TestCase):
    def setUp(self):
        User = get_user_model()
        u = User.objects.create_user(username="u", password="p")
        Parcela.objects.create(
            nombre="Parcela 1",
            ubicacion="Location 1",
            tamano_hectareas=10.00,
            coordenadas="12.3456,-76.5432",
            altitud=100.00,
            tipo_cultivo="Maíz",
            usuario=u,
        )

    def test_parcela_creation(self):
        p = Parcela.objects.get(nombre="Parcela 1")
        assert p.ubicacion == "Location 1"
        assert float(p.tamano_hectareas) == 10.00
        assert p.tipo_cultivo == "Maíz"

    def test_parcela_str(self):
        p = Parcela.objects.get(nombre="Parcela 1")
        assert p.nombre in str(p)