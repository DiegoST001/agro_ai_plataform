from datetime import datetime, timezone
from django.utils import timezone
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample
from .auth import NodeTokenAuthentication
from .models import Node, NodoSecundario
from .mongo import db  # Importa la conexión a MongoDB
from .serializers import NodeSerializer, NodoSecundarioSerializer

def readings_collection(name):
    """Devuelve la colección de lecturas en MongoDB."""
    return db[name]

@extend_schema(
    tags=['Ingesta'],
    summary='Ingesta de datos desde nodo maestro',
    description=(
        "Recibe datos de sensores enviados por el nodo maestro y los almacena en MongoDB. "
        "El payload puede incluir información opcional como batería, latitud, longitud, estado y señal, además de los datos requeridos. "
        "Este endpoint es usado por los dispositivos físicos para enviar telemetría."
    ),
    request={
        "type": "object",
        "properties": {
            "parcela_id": {"type": "integer", "example": 1},
            "codigo_nodo_maestro": {"type": "string", "example": "NODE-001"},
            "timestamp": {"type": "string", "format": "date-time", "example": "2025-09-24T18:30:00Z"},
            "last_seen": {"type": "string", "format": "date-time", "example": "2025-10-01T07:59:50Z"},
            "estado": {"type": "string", "example": "activo"},
            "lat": {"type": "string", "example": "-13.53"},
            "lng": {"type": "string", "example": "-70.65"},
            "senal": {"type": "string", "example": "-70dBm"},
            "lecturas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "nodo_codigo": {"type": "string", "example": "NODE-01"},
                        "bateria": {"type": "integer", "example": 95},
                        "last_seen": {"type": "string", "format": "date-time", "example": "2025-10-01T07:59:50Z"},
                        "sensores": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "sensor": {"type": "string", "example": "temperatura"},
                                    "valor": {"type": "number", "example": 22.5},
                                    "unidad": {"type": "string", "example": "°C"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "required": ["parcela_id", "codigo_nodo_maestro", "timestamp", "lecturas"]
    },
    examples=[
        OpenApiExample(
            'Payload ejemplo',
            value={
                "parcela_id": 5,
                "codigo_nodo_maestro": "NODE-001",
                "last_seen": "2025-10-01T07:59:50Z",
                "estado": "activo",
                "lat": "-13.53",
                "lng": "-70.65",
                "senal": "-70dBm",
                "timestamp": "2025-10-01T08:00:00Z",
                "lecturas": [
                    {
                        "nodo_codigo": "NODE-01",
                        "bateria": 95,
                        "last_seen": "2025-10-01T07:59:50Z",
                        "sensores": [
                            { "sensor": "temperatura", "valor": 22.5, "unidad": "°C" },
                            { "sensor": "humedad", "valor": 65.2, "unidad": "%" }
                        ]
                    }
                ]
            }
        )
    ],
    responses={
        200: OpenApiExample(
            'Respuesta exitosa',
            value={"detail": "OK"}
        ),
        400: OpenApiExample(
            'Error',
            value={"detail": "Payload inválido"}
        )
    }
)
class NodeIngestView(views.APIView):
    authentication_classes = [NodeTokenAuthentication]
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        payload = request.data or {}

        # Guarda solo lo esencial en MongoDB
        mongo_doc = {
            "parcela_id": payload.get("parcela_id"),
            "codigo_nodo_maestro": payload.get("codigo_nodo_maestro"),
            "timestamp": payload.get("timestamp"),
            "lecturas": []
        }
        for lectura in payload.get("lecturas", []):
            lectura_doc = {
                "nodo_codigo": lectura.get("nodo_codigo"),
                "last_seen": lectura.get("last_seen"),
                "sensores": lectura.get("sensores", [])
            }
            mongo_doc["lecturas"].append(lectura_doc)
        readings_collection("lecturas_sensores").insert_one(mongo_doc)

        # Actualiza estado y last_seen del nodo maestro en la base relacional
        try:
            node = Node.objects.get(codigo=payload.get("codigo_nodo_maestro"))
            node.last_seen = timezone.now()
            node.estado = "activo"
            node.save(update_fields=["last_seen", "estado"])
        except Node.DoesNotExist:
            pass

        # Actualiza estado y last_seen de los nodos secundarios en la base relacional
        for lectura in payload.get("lecturas", []):
            try:
                nodo_sec = NodoSecundario.objects.get(codigo=lectura.get("nodo_codigo"))
                nodo_sec.last_seen = timezone.now()
                nodo_sec.estado = "activo"
                nodo_sec.save(update_fields=["last_seen", "estado"])
            except NodoSecundario.DoesNotExist:
                pass

        return Response({'detail': 'OK'}, status=status.HTTP_200_OK)

@extend_schema(
    tags=['Nodos'],
    summary='Listar nodos maestros de una parcela',
    description='Devuelve todos los nodos maestros asociados a una parcela específica. Útil para administración y visualización por parcela.',
)
class NodoMasterListView(generics.ListAPIView):
    serializer_class = NodeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        parcela_id = self.kwargs.get('parcela_id')
        return Node.objects.filter(parcela_id=parcela_id)

@extend_schema(
    tags=['Nodos'],
    summary='Listar nodos secundarios de un nodo maestro',
    description='Devuelve todos los nodos secundarios asociados a un nodo maestro específico. Útil para ver la red de sensores de cada nodo maestro.',
)
class NodoSecundarioListView(generics.ListAPIView):
    serializer_class = NodoSecundarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        nodo_master_id = self.kwargs.get('nodo_master_id')
        return NodoSecundario.objects.filter(maestro_id=nodo_master_id)

from drf_spectacular.utils import extend_schema

@extend_schema(
    tags=['Nodos'],
    summary='Crear nodo maestro para una parcela',
    description='Permite crear un nodo maestro y asociarlo a una parcela. El código del nodo se genera automáticamente y es único.',
    request=NodeSerializer,
    responses=NodeSerializer,
    examples=[
        OpenApiExample(
            'Ejemplo de creación de nodo maestro',
            value={
                "lat": -13.53,
                "lng": -70.65,
                "estado": "activo",
                "bateria": 95,
                "senal": -70,
                "last_seen": "2025-10-12T10:28:56.159Z"
            },
            request_only=True
        )
    ]
)
class NodeCreateView(generics.CreateAPIView):
    serializer_class = NodeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        parcela_id = self.kwargs.get('parcela_id')
        serializer.save(parcela_id=parcela_id)

@extend_schema(
    tags=['Nodos'],
    summary='Actualizar nodo maestro',
    description='Permite actualizar los datos de un nodo maestro existente. No se puede modificar el código generado automáticamente.',
    request=NodeSerializer,
    responses=NodeSerializer,
)
class NodeUpdateView(generics.UpdateAPIView):
    serializer_class = NodeSerializer
    queryset = Node.objects.all()
    permission_classes = [permissions.IsAuthenticated]

@extend_schema(
    tags=['Nodos'],
    summary='Crear nodo secundario para un nodo maestro',
    description=(
        "Permite crear un nodo secundario asociado a un nodo maestro específico. "
        "El código del nodo secundario se genera automáticamente y es único, incluyendo el código del maestro."
    ),
    request=NodoSecundarioSerializer,
    responses=NodoSecundarioSerializer,
    examples=[
        OpenApiExample(
            'Ejemplo de creación de nodo secundario',
            value={
                "estado": "activo",
                "bateria": 90,
                "last_seen": "2025-10-12T10:30:00.000Z"
            },
            request_only=True
        )
    ]
)
class NodoSecundarioCreateView(generics.CreateAPIView):
    serializer_class = NodoSecundarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        maestro_id = self.kwargs.get('nodo_master_id')
        serializer.save(maestro_id=maestro_id)

@extend_schema(
    tags=['Nodos'],
    summary='Listar todos los nodos maestros',
    description='Devuelve todos los nodos maestros registrados en el sistema. Útil para administración general.',
)
class NodeListView(generics.ListAPIView):
    serializer_class = NodeSerializer
    queryset = Node.objects.all()
    permission_classes = [permissions.IsAuthenticated]

@extend_schema(
    tags=['Nodos'],
    summary='Detalle de nodo maestro',
    description=(
        "Devuelve los datos completos de un nodo maestro, incluyendo sus nodos secundarios asociados. "
        "Ideal para ver la configuración y estado de toda la red de sensores de un nodo maestro."
    ),
)
class NodeDetailView(generics.RetrieveAPIView):
    serializer_class = NodeSerializer
    queryset = Node.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['include_secundarios'] = True
        return ctx