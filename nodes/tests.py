from django.test import TestCase
from .models import NodosMaestros, NodosSecundarios, TokensNodos

class NodosMaestrosModelTest(TestCase):
    def setUp(self):
        self.nodo_maestro = NodosMaestros.objects.create(
            codigo="NODE-001",
            parcela_id=1,
            lat=12.345678,
            lng=98.765432,
            estado="activo",
            bateria=100,
            señal=75,
            last_seen="2025-09-01T18:30:00Z"
        )

    def test_nodo_maestro_creation(self):
        self.assertEqual(self.nodo_maestro.codigo, "NODE-001")
        self.assertEqual(self.nodo_maestro.estado, "activo")

class NodosSecundariosModelTest(TestCase):
    def setUp(self):
        self.nodo_maestro = NodosMaestros.objects.create(
            codigo="NODE-001",
            parcela_id=1,
            lat=12.345678,
            lng=98.765432,
            estado="activo",
            bateria=100,
            señal=75,
            last_seen="2025-09-01T18:30:00Z"
        )
        self.nodo_secundario = NodosSecundarios.objects.create(
            codigo="NODE-002",
            maestro_id=self.nodo_maestro.id,
            lat=12.345679,
            lng=98.765433,
            estado="activo",
            bateria=90,
            señal=70,
            last_seen="2025-09-01T18:30:00Z"
        )

    def test_nodo_secundario_creation(self):
        self.assertEqual(self.nodo_secundario.codigo, "NODE-002")
        self.assertEqual(self.nodo_secundario.estado, "activo")

class TokensNodosModelTest(TestCase):
    def setUp(self):
        self.nodo_maestro = NodosMaestros.objects.create(
            codigo="NODE-001",
            parcela_id=1,
            lat=12.345678,
            lng=98.765432,
            estado="activo",
            bateria=100,
            señal=75,
            last_seen="2025-09-01T18:30:00Z"
        )
        self.token_nodo = TokensNodos.objects.create(
            nodo_id=self.nodo_maestro.id,
            token="TOKEN-12345",
            fecha_creacion="2025-09-01T18:30:00Z",
            fecha_expiracion="2025-09-02T18:30:00Z",
            estado="valido"
        )

    def test_token_nodo_creation(self):
        self.assertEqual(self.token_nodo.token, "TOKEN-12345")
        self.assertEqual(self.token_nodo.estado, "valido")