from django.test import TestCase
from .models import SensorReading

class SensorReadingModelTest(TestCase):
    def setUp(self):
        SensorReading.objects.create(
            nodo_id="NODE-12345",
            parcela_id=1,
            sensor_tipo="HumedadSuelo",
            valor=35.6,
            unidad="%",
            timestamp="2025-09-01T18:30:00Z"
        )

    def test_sensor_reading_creation(self):
        reading = SensorReading.objects.get(nodo_id="NODE-12345")
        self.assertEqual(reading.valor, 35.6)
        self.assertEqual(reading.sensor_tipo, "HumedadSuelo")
        self.assertEqual(reading.unidad, "%")