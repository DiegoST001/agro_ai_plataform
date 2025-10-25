from datetime import datetime, timezone
from django.utils import timezone
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample
from .auth import NodeTokenAuthentication
from .models import Node, NodoSecundario, Parcela
from agro_ai_platform.mongo import get_db
from .serializers import NodeSerializer, NodoSecundarioSerializer
# reemplazado: import directo de helpers de permisos del app nodes (reusa users.permissions)
from .permissions import tiene_permiso, role_name, HasOperationPermission, OwnsObjectOrAdmin
from rest_framework.exceptions import PermissionDenied, NotFound


def readings_collection(name):
    # usa get_db() de forma lazy para evitar import-time issues
    db = get_db()
    return db[name]

@extend_schema(
    tags=['Ingesta'],
    summary='Ingesta de datos desde nodo maestro',
    description="Recibe datos de sensores enviados por el nodo maestro y los almacena en MongoDB. El payload puede incluir información opcional.",
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
        # 0) autenticación por token de nodo (NodeTokenAuthentication debe setear request.node y request.auth)
        token = getattr(request, "auth", None)
        nodo_auth = getattr(request, "node", None)
        if not token or not nodo_auth:
            return Response({'detail': 'No autorizado'}, status=status.HTTP_401_UNAUTHORIZED)

        payload = request.data or {}
        # normalizar timestamp (acepta ISO string o None)
        ts = payload.get("timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                ts = None

        mongo_doc = {
            "seed_tag": payload.get("seed_tag", "demo"),
            "parcela_id": payload.get("parcela_id"),
            "codigo_nodo_maestro": payload.get("codigo_nodo_maestro"),
            "timestamp": ts or timezone.now(),
            "lecturas": []
        }
        # recopilar códigos presentes en el payload
        present_codes = set()
        for lectura in payload.get("lecturas", []):
            codigo = lectura.get("nodo_codigo")
            lectura_doc = {
                "nodo_codigo": codigo,
                "last_seen": lectura.get("last_seen"),
                "sensores": lectura.get("sensores", []),
            }
            if "bateria" in lectura:
                lectura_doc["bateria"] = lectura.get("bateria")
            mongo_doc["lecturas"].append(lectura_doc)
            if codigo:
                present_codes.add(codigo)
        try:
            readings_collection("lecturas_sensores").insert_one(mongo_doc)
        except Exception as e:
            return Response({'detail': 'Error al insertar en MongoDB', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # preferir nodo autenticado por token; si no, fallback por código
        node = nodo_auth or Node.objects.filter(codigo=payload.get("codigo_nodo_maestro")).first()
        now = timezone.now()
        if node:
            node.last_seen = now
            # marcar activo por defecto al recibir ingestión, salvo que el payload especifique otro estado
            node.estado = payload.get("estado", "activo")
            update_fields = ["last_seen", "estado"]

            if "bateria" in payload and payload.get("bateria") is not None:
                try:
                    node.bateria = int(payload.get("bateria"))
                    update_fields.append("bateria")
                except (ValueError, TypeError):
                    pass

            if "senal" in payload and payload.get("senal") is not None:
                try:
                    node.senal = int(payload.get("senal"))
                    update_fields.append("senal")
                except (ValueError, TypeError):
                    pass

            if "lat" in payload and payload.get("lat") is not None:
                node.lat = payload.get("lat")
                update_fields.append("lat")
            if "lng" in payload and payload.get("lng") is not None:
                node.lng = payload.get("lng")
                update_fields.append("lng")

            node.save(update_fields=list(dict.fromkeys(update_fields)))
        else:
            # si no hubo nodo (improbable porque auth debería darlo), seguir igualmente
            pass

        # actualizar nodos secundarios presentes y marcar como inactivos los ausentes
        # primero actualizar los que vienen en el payload
        for lectura in payload.get("lecturas", []):
            codigo_sec = lectura.get("nodo_codigo")
            if not codigo_sec:
                continue
            try:
                nodo_sec = NodoSecundario.objects.get(codigo=codigo_sec)
                changed_fields = []
                # always update last_seen if provided
                if lectura.get("last_seen") is not None:
                    try:
                        nodo_sec.last_seen = lectura.get("last_seen")
                        changed_fields.append("last_seen")
                    except Exception:
                        pass
                # marcar activo por defecto si aparece en el payload (a menos que venga otro estado)
                estado_val = lectura.get("estado", "activo")
                if estado_val is not None:
                    nodo_sec.estado = estado_val
                    changed_fields.append("estado")
                # batería (acepta 0)
                if "bateria" in lectura and lectura.get("bateria") is not None:
                    try:
                        nodo_sec.bateria = int(lectura.get("bateria"))
                        changed_fields.append("bateria")
                    except (ValueError, TypeError):
                        pass
                if changed_fields:
                    nodo_sec.save(update_fields=list(dict.fromkeys(changed_fields)))
            except NodoSecundario.DoesNotExist:
                continue

        # si conocemos el maestro, marcar como 'inactivo' los secundarios de ese maestro
        # cuyo codigo NO esté en present_codes
        if node is not None:
            qs_absent = NodoSecundario.objects.filter(maestro=node)
            if present_codes:
                qs_absent = qs_absent.exclude(codigo__in=list(present_codes))
            # actualizar solo los que realmente cambien para evitar write churn
            qs_absent.update(estado="inactivo")

        return Response({"detail": "OK"}, status=status.HTTP_200_OK)

@extend_schema(
    tags=['Nodos'],
    summary='Listar nodos maestros de una parcela',
    description='Devuelve todos los nodos maestros asociados a una parcela específica.',
)
class NodoMasterListView(generics.ListAPIView):
    serializer_class = NodeSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'ver')]

    def get_queryset(self):
        user = self.request.user
        parcela_id = self.kwargs.get('parcela_id')

        # verificar existencia de parcela -> 404 si no existe
        try:
            parcela = Parcela.objects.get(id=parcela_id)
        except Parcela.DoesNotExist:
            raise NotFound(detail="Parcela no existe.")

        # permiso de módulo
        if not tiene_permiso(user, 'nodos', 'ver'):
            raise PermissionDenied(detail="No tienes permiso para ver nodos.")

        # admin puede ver todo; agricultor solo sus parcelas
        if role_name(user) in ['superadmin', 'administrador']:
            return Node.objects.filter(parcela_id=parcela_id)
        if parcela.usuario == user:
            return Node.objects.filter(parcela_id=parcela_id)

        raise PermissionDenied(detail="No tienes permiso para ver los nodos de esta parcela.")

@extend_schema(
    tags=['Nodos'],
    summary='Listar nodos secundarios de un nodo maestro',
    description='Devuelve todos los nodos secundarios asociados a un nodo maestro específico.',
)
class NodoSecundarioListView(generics.ListAPIView):
    serializer_class = NodoSecundarioSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'ver')]

    def get_queryset(self):
        user = self.request.user
        nodo_master_id = self.kwargs.get('nodo_master_id')

        # comprobar existencia del maestro -> 404
        try:
            nodo_master = Node.objects.select_related('parcela').get(id=nodo_master_id)
        except Node.DoesNotExist:
            raise NotFound(detail="Nodo maestro no existe.")

        # permiso de módulo
        if not tiene_permiso(user, 'nodos', 'ver'):
            raise PermissionDenied(detail="No tienes permiso para ver nodos.")

        # admin puede ver siempre
        if role_name(user) in ['superadmin', 'administrador']:
            return NodoSecundario.objects.filter(maestro_id=nodo_master_id)

        # propietario de la parcela puede ver
        if getattr(nodo_master.parcela, 'usuario', None) == user:
            return NodoSecundario.objects.filter(maestro_id=nodo_master_id)

        raise PermissionDenied(detail="No tienes permiso para ver los nodos secundarios de este nodo maestro.")

@extend_schema(
    tags=['Nodos'],
    summary='Crear nodo maestro para una parcela',
    description='Permite crear un nodo maestro y asociarlo a una parcela. El código se genera automáticamente.',
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

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'crear')]

    def perform_create(self, serializer):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'crear'):
            raise PermissionDenied("No tienes permiso para crear nodos.")
        parcela_id = self.kwargs.get('parcela_id')
        # verificar existencia de parcela -> 404
        try:
            parcela = Parcela.objects.get(id=parcela_id)
        except Parcela.DoesNotExist:
            raise NotFound(detail="Parcela no existe.")
        if role_name(user) == 'agricultor' and parcela.usuario != user:
            raise PermissionDenied("No puedes crear nodos en parcelas que no son tuyas.")
        serializer.save(parcela_id=parcela_id)

@extend_schema(
    tags=['Nodos'],
    summary='Actualizar nodo maestro',
    description='Permite actualizar los datos de un nodo maestro existente.',
    request=NodeSerializer,
    responses=NodeSerializer,
)
class NodeUpdateView(generics.UpdateAPIView):
    serializer_class = NodeSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'actualizar'), OwnsObjectOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'actualizar'):
            raise PermissionDenied(detail="No tienes permiso para actualizar nodos.")
        if role_name(user) == 'agricultor':
            return Node.objects.filter(parcela__usuario=user)
        return Node.objects.all()

@extend_schema(
    tags=['Nodos'],
    summary='Crear nodo secundario para un nodo maestro',
    description='Permite crear un nodo secundario asociado a un nodo maestro específico.',
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

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'crear')]

    def perform_create(self, serializer):
        user = self.request.user
        maestro_id = self.kwargs.get('nodo_master_id')
        try:
            nodo_master = Node.objects.select_related('parcela').get(id=maestro_id)
        except Node.DoesNotExist:
            raise NotFound(detail="Nodo maestro no existe.")
        # permiso de módulo
        if not tiene_permiso(user, 'nodos', 'crear'):
            raise PermissionDenied(detail="No tienes permiso para crear nodos secundarios.")
        if role_name(user) in ['superadmin', 'administrador'] or getattr(nodo_master.parcela, 'usuario', None) == user:
            serializer.save(maestro_id=maestro_id)
            return
        raise PermissionDenied(detail="No tienes permiso para crear nodos secundarios en este nodo maestro.")

@extend_schema(
    tags=['Nodos'],
    summary='Listar todos los nodos maestros',
    description='Devuelve todos los nodos maestros registrados en el sistema.',
)
class NodeListView(generics.ListAPIView):
    serializer_class = NodeSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'ver')]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'ver'):
            raise PermissionDenied(detail="No tienes permiso para ver nodos.")
        if role_name(user) == 'agricultor':
            parcelas = Parcela.objects.filter(usuario=user)
            return Node.objects.filter(parcela__in=parcelas)
        return Node.objects.all()

@extend_schema(
    tags=['Nodos'],
    summary='Detalle de nodo maestro',
    description='Devuelve los datos completos de un nodo maestro, incluyendo sus nodos secundarios asociados.',
)
class NodeDetailView(generics.RetrieveAPIView):
    serializer_class = NodeSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'ver'), OwnsObjectOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'ver'):
            raise PermissionDenied(detail="No tienes permiso para ver nodos.")
        if role_name(user) in ['superadmin', 'administrador']:
            return Node.objects.all()
        return Node.objects.filter(parcela__usuario=user)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['include_secundarios'] = True
        return ctx

@extend_schema(
    tags=['Nodos'],
    summary='Eliminar nodo maestro',
    description='Permite eliminar un nodo maestro existente.',
)
class NodeDeleteView(generics.DestroyAPIView):
    serializer_class = NodeSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'eliminar'), OwnsObjectOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'eliminar'):
            raise PermissionDenied(detail="No tienes permiso para eliminar nodos.")
        if role_name(user) == 'agricultor':
            return Node.objects.filter(parcela__usuario=user)
        return Node.objects.all()

@extend_schema(
    tags=['Nodos'],
    summary='Eliminar nodo secundario',
    description='Permite eliminar un nodo secundario existente.',
)
class NodoSecundarioDeleteView(generics.DestroyAPIView):
    serializer_class = NodoSecundarioSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'eliminar'), OwnsObjectOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'eliminar'):
            raise PermissionDenied(detail="No tienes permiso para eliminar nodos secundarios.")
        if role_name(user) == 'agricultor':
            return NodoSecundario.objects.filter(maestro__parcela__usuario=user)
        return NodoSecundario.objects.all()

@extend_schema(
    tags=['Nodos'],
    summary='Listar todos los nodos secundarios',
    description='Devuelve todos los nodos secundarios registrados en el sistema.',
)
class NodoSecundarioListAllView(generics.ListAPIView):
    serializer_class = NodoSecundarioSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'ver')]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'ver'):
            raise PermissionDenied(detail="No tienes permiso para ver nodos secundarios.")
        if role_name(user) == 'agricultor':
            return NodoSecundario.objects.filter(maestro__parcela__usuario=user)
        return NodoSecundario.objects.all()

@extend_schema(
    tags=['Nodos'],
    summary='Detalle de nodo secundario',
    description='Devuelve los datos completos de un nodo secundario.',
)
class NodoSecundarioDetailView(generics.RetrieveAPIView):
    serializer_class = NodoSecundarioSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'ver'), OwnsObjectOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'ver'):
            raise PermissionDenied(detail="No tienes permiso para ver nodos secundarios.")
        if role_name(user) in ['superadmin', 'administrador']:
            return NodoSecundario.objects.all()
        return NodoSecundario.objects.filter(maestro__parcela__usuario=user)

@extend_schema(
    tags=['Nodos'],
    summary='Actualizar nodo secundario',
    description='Permite actualizar los datos de un nodo secundario existente.',
    request=NodoSecundarioSerializer,
    responses=NodoSecundarioSerializer,
)
class NodoSecundarioUpdateView(generics.UpdateAPIView):
    serializer_class = NodoSecundarioSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('nodos', 'actualizar'), OwnsObjectOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'nodos', 'actualizar'):
            raise PermissionDenied(detail="No tienes permiso para actualizar nodos secundarios.")
        if role_name(user) == 'agricultor':
            return NodoSecundario.objects.filter(maestro__parcela__usuario=user)
        return NodoSecundario.objects.all()