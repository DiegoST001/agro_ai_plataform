from datetime import datetime, timezone
from rest_framework import permissions, status, views
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample
from .auth import NodeTokenAuthentication
from .models import Node, NodoSecundario
from sensors.models import Sensor
from sensors.mongo import readings_collection

@extend_schema(
    tags=['Ingesta'],
    summary='Ingesta de datos desde nodo maestro',
    examples=[
        OpenApiExample(
            'Payload ejemplo',
            value={
                "node_code": "NODE-001",
                "battery": 82,
                "signal": 3,
                "lat": -13.52,
                "lng": -71.97,
                "secondary": [
                    {"code":"SN-1","battery":70,"signal":2,"lat":-13.52,"lng":-71.971}
                ],
                "readings": [
                    {"sensor_id":"S-1","collection":"lecturas_sensores","type":"HumedadSuelo","value":35.6,"unit":"%","timestamp":"2025-09-24T18:30:00Z"}
                ]
            }
        )
    ]
)
class NodeIngestView(views.APIView):
    authentication_classes = [NodeTokenAuthentication]
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # Autenticación por token de nodo
        token = getattr(request, 'auth', None)
        if not token or not getattr(request, 'node', None):
            return Response({'detail': 'No autorizado'}, status=status.HTTP_401_UNAUTHORIZED)

        nodo: Node = request.node
        payload = request.data or {}

        # 1) Actualiza estado del nodo maestro
        nodo.bateria = payload.get('battery', nodo.bateria)
        nodo.senal = payload.get('signal', nodo.senal)
        nodo.lat = payload.get('lat', nodo.lat)
        nodo.lng = payload.get('lng', nodo.lng)
        nodo.last_seen = datetime.now(timezone.utc)
        nodo.save(update_fields=['bateria','senal','lat','lng','last_seen','updated_at'])

        # 2) Actualiza/crea secundarios
        for sn in payload.get('secondary', []):
            sec, _ = NodoSecundario.objects.get_or_create(
                codigo=sn.get('code'),
                defaults={'maestro': nodo}
            )
            if sec.maestro_id != nodo.id:
                sec.maestro = nodo
            sec.bateria = sn.get('battery', sec.bateria)
            sec.senal = sn.get('signal', sec.senal)
            sec.lat = sn.get('lat', sec.lat)
            sec.lng = sn.get('lng', sec.lng)
            sec.last_seen = datetime.now(timezone.utc)
            sec.save()

        # 3) Inserta lecturas en Mongo
        inserted = 0
        for r in payload.get('readings', []):
            collection = r.get('collection') or 'lecturas_sensores'
            doc = {
                'nodo_id': nodo.codigo,
                'parcela_id': nodo.parcela_id,
                'sensor_id': r.get('sensor_id'),
                'sensor_tipo': r.get('type'),
                'valor': r.get('value'),
                'unidad': r.get('unit'),
                'timestamp': r.get('timestamp') or datetime.now(timezone.utc),
            }
            readings_collection(collection).insert_one(doc)
            inserted += 1

            # Opcional: si mapeas sensor_id con tu modelo Sensor, puedes validar pertenencia
            # Sensor.objects.filter(ext_sensor_id=doc['sensor_id']).exists()

        return Response({'detail': 'OK', 'mongo_inserted': inserted}, status=status.HTTP_200_OK)