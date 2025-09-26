from django.test import TestCase
from django.contrib.auth import get_user_model
from parcels.models import Parcela
from .models import Recommendation

class RecommendationModelTest(TestCase):
    def setUp(self):
        User = get_user_model()
        u = User.objects.create_user(username="u", password="p")
        parcela = Parcela.objects.create(
            usuario=u, nombre="P", ubicacion="", tamano_hectareas=1
        )
        Recommendation.objects.create(
            parcela=parcela,
            titulo="Recomendación de prueba",
            detalle="Detalle",
            tipo="general",
        )

    def test_recommendation_creation(self):
        r = Recommendation.objects.get(titulo="Recomendación de prueba")
        assert r.detalle == "Detalle"
        assert r.estado == "nuevo"