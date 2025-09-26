from django.test import TestCase
from .models import Task, Recommendation

class TaskModelTest(TestCase):
    def setUp(self):
        self.recommendation = Recommendation.objects.create(
            tipo='regar',
            descripcion='Regar la parcela',
            estado='pendiente',
            parcela_id=1
        )
        self.task = Task.objects.create(
            parcela_id=1,
            recomendacion_id=self.recommendation.id,
            tipo='regar',
            descripcion='Tarea de riego programada',
            fecha_programada='2025-09-01T18:30:00Z',
            estado='pendiente',
            origen='ia'
        )

    def test_task_creation(self):
        self.assertEqual(self.task.tipo, 'regar')
        self.assertEqual(self.task.descripcion, 'Tarea de riego programada')
        self.assertEqual(self.task.estado, 'pendiente')
        self.assertEqual(self.task.origen, 'ia')

    def test_task_recommendation_relationship(self):
        self.assertEqual(self.task.recomendacion_id, self.recommendation.id)

    def test_task_str(self):
        self.assertEqual(str(self.task), 'Tarea de riego programada')  # Assuming __str__ method is defined in Task model