from django.test import TestCase
from .models import Alerta

class AlertaModelTest(TestCase):

    def setUp(self):
        Alerta.objects.create(
            tipo="Error",
            severidad="Alta",
            mensaje="Fallo en el sensor de humedad.",
            fecha_generacion="2025-09-01T18:30:00Z",
            parcela_id=1
        )

    def test_alerta_creation(self):
        alerta = Alerta.objects.get(tipo="Error")
        self.assertEqual(alerta.severidad, "Alta")
        self.assertEqual(alerta.mensaje, "Fallo en el sensor de humedad.")
        self.assertIsNotNone(alerta.fecha_generacion)