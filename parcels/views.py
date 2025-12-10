from django.utils import timezone
from datetime import date

from rest_framework import permissions, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.parsers import JSONParser
import cloudinary.uploader

from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter, OpenApiTypes, OpenApiExample
from users.permissions import HasOperationPermission, role_name, tiene_permiso

# models
from .models import Parcela, Ciclo, ParcelaImage
# serializers (asegúrate que ParcelaImageSerializer esté definido en serializers.py)
from .serializers import (
    CicloCreateSerializer,
    CicloReadSerializer,
    ParcelaCreateSerializer,
    ParcelaReadSerializer,
    ParcelaUpdateSerializer,
    ParcelaImageSerializer
)

# ----------------------------------------
# Ciclo endpoints
# ----------------------------------------
@extend_schema_view(
    get=extend_schema(
        tags=['ciclos'],
        summary='Listar ciclos de una parcela',
        description=(
            "Lista los ciclos (campañas) asociados a una parcela.\n\n"
            "Requiere permiso: `parcelas.ver`.\n\n"
            "Respuesta: paginada con objetos `CicloReadSerializer`."
        ),
        parameters=[OpenApiParameter(name='parcela_id', type=OpenApiTypes.INT, location=OpenApiParameter.PATH)],
        responses={200: CicloReadSerializer(many=True)},
        examples=[
            OpenApiExample('Respuesta ejemplo', value=[{
                "id": 1,
                "cultivo": {"id": 2, "nombre": "Palta"},
                "variedad": {"id": 5, "nombre": "Hass"},
                "etapa_actual": {"id": 9, "nombre": "Floración"},
                "etapa_inicio": "2025-10-01",
                "estado": "activo",
                "fecha_cierre": None
            }], response_only=True)
        ]
    ),
    post=extend_schema(
        tags=['ciclos'],
        summary='Crear ciclo en parcela',
        description=(
            "Crear un nuevo ciclo en la parcela indicada.\n\n"
            "Requiere permiso: `parcelas.crear`.\n"
            "Validaciones: variedad debe pertenecer al cultivo; etapa a la variedad."
        ),
        request=CicloCreateSerializer,
        responses={201: CicloReadSerializer},
        examples=[
            OpenApiExample('Crear ejemplo', value={"cultivo": 2, "variedad": 5, "etapa_actual": 9, "etapa_inicio": "2025-10-01"}, request_only=True)
        ]
    )
)
class ParcelaCicloListCreateView(generics.ListCreateAPIView):
    """
    Lista y crea ciclos para una parcela concreta.
    """
    def get_permissions(self):
        op = 'ver' if self.request.method == 'GET' else 'crear'
        return [permissions.IsAuthenticated(), HasOperationPermission('parcelas', op)]

    def get_serializer_class(self):
        return CicloReadSerializer if self.request.method == 'GET' else CicloCreateSerializer

    def _get_parcela_or_403(self):
        from rest_framework.exceptions import PermissionDenied, NotFound
        parcela_id = self.kwargs.get('parcela_id')
        try:
            parcela = Parcela.objects.select_related('usuario').get(pk=parcela_id)
        except Parcela.DoesNotExist:
            raise NotFound("Parcela no encontrada.")
        r = role_name(self.request.user)
        if r not in ['superadmin', 'administrador', 'tecnico'] and parcela.usuario_id != self.request.user.id:
            raise PermissionDenied("No puede acceder a ciclos de una parcela que no es suya.")
        return parcela

    def get_queryset(self):
        # permiso por 'parcelas.ver'
        if not tiene_permiso(self.request.user, 'parcelas', 'ver'):
            return Ciclo.objects.none()
        parcela = self._get_parcela_or_403()
        return Ciclo.objects.filter(parcela=parcela).select_related('cultivo', 'variedad', 'etapa_actual').order_by('-created_at')

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied, ValidationError
        # permiso por 'parcelas.crear'
        if not tiene_permiso(self.request.user, 'parcelas', 'crear'):
            raise PermissionDenied("No tiene permiso para crear ciclos.")
        parcela = self._get_parcela_or_403()

        data = serializer.validated_data
        cultivo = data.get('cultivo')
        variedad = data.get('variedad')
        etapa = data.get('etapa_actual')

        if variedad and cultivo and variedad.cultivo_id != cultivo.id:
            raise ValidationError({"variedad": "La variedad no pertenece al cultivo indicado."})
        if etapa and variedad and etapa.variedad_id != variedad.id:
            raise ValidationError({"etapa_actual": "La etapa no pertenece a la variedad indicada."})

        serializer.save(parcela=parcela)


@extend_schema_view(
    get=extend_schema(
        tags=['ciclos'],
        summary='Detalle de ciclo',
        description="Recupera/actualiza/elimina un ciclo por su id. Válidos: GET/PUT/PATCH/DELETE.",
        responses={200: CicloReadSerializer}
    ),
    put=extend_schema(tags=['ciclos'], summary='Actualizar ciclo', request=CicloCreateSerializer, responses={200: CicloReadSerializer}),
    patch=extend_schema(tags=['ciclos'], summary='Actualizar parcialmente ciclo', request=CicloCreateSerializer, responses={200: CicloReadSerializer}),
    delete=extend_schema(tags=['ciclos'], summary='Eliminar ciclo', responses={204: None})
)
class CicloDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CicloReadSerializer

    def _op(self):
        if self.request.method == 'GET':
            return 'ver'
        if self.request.method in ['PUT', 'PATCH']:
            return 'actualizar'
        if self.request.method == 'DELETE':
            return 'eliminar'
        return 'ver'

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('parcelas', self._op())]

    def get_queryset(self):
        user = self.request.user
        op = self._op()
        if not tiene_permiso(user, 'parcelas', op):
            return Ciclo.objects.none()
        r = role_name(user)
        qs = Ciclo.objects.select_related('parcela__usuario', 'cultivo', 'variedad', 'etapa_actual')
        if r in ['superadmin', 'administrador', 'tecnico']:
            return qs
        return qs.filter(parcela__usuario=user)


class CicloAdvanceEtapaView(APIView):
    """
    Avanza la etapa de un ciclo si corresponde por duración o forzadamente.
    POST body optional: {"force": true}
    """
    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('parcelas', 'actualizar')]

    @extend_schema(
        tags=['ciclos'],
        summary='Avanzar etapa del ciclo',
        description=(
            "Avanza la etapa actual de un ciclo.\n\n"
            "- `force=true` fuerza el avance a la siguiente etapa activa.\n"
            "- Si no hay siguiente etapa devuelve `{advanced:false}`.\n"
            "Requiere permiso: `parcelas.actualizar`."
        ),
        request={'type': 'object', 'properties': {'force': {'type': 'boolean'}}},
        responses={
            200: OpenApiExample('Avance', value={"advanced": True, "ciclo_id": 1, "etapa_actual": {"id": 4, "nombre": "Maduración"}, "etapa_inicio": "2025-10-28"})
        }
    )
    def post(self, request, pk):
        from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
        try:
            ciclo = Ciclo.objects.select_related('parcela__usuario', 'etapa_actual', 'etapa_actual__variedad').get(pk=pk)
        except Ciclo.DoesNotExist:
            raise NotFound("Ciclo no encontrado.")

        r = role_name(request.user)
        if r not in ['superadmin', 'administrador', 'tecnico'] and ciclo.parcela.usuario_id != request.user.id:
            raise PermissionDenied("No puede modificar ciclos de otra persona.")

        force = bool(request.data.get('force'))
        advanced = False

        if force:
            etapa_actual = ciclo.etapa_actual
            if not etapa_actual:
                raise ValidationError({"etapa_actual": "El ciclo no tiene etapa actual para avanzar."})
            siguiente = Etapa.objects.filter(
                variedad=etapa_actual.variedad,
                orden__gt=etapa_actual.orden,
                activo=True
            ).order_by('orden').first()
            if not siguiente:
                return Response({"advanced": False, "detail": "No existe una siguiente etapa activa."}, status=status.HTTP_200_OK)
            ciclo.etapa_actual = siguiente
            start = timezone.now().date()
            if ciclo.etapa_inicio:
                start = ciclo.etapa_inicio
            ciclo.etapa_inicio = start
            ciclo.save(update_fields=['etapa_actual', 'etapa_inicio', 'updated_at'])
            advanced = True
        else:
            advanced = ciclo.advance_etapa_if_needed()

        ciclo_ref = Ciclo.objects.select_related('etapa_actual').get(pk=ciclo.pk)
        return Response({
            "advanced": advanced,
            "ciclo_id": ciclo_ref.id,
            "etapa_actual": (
                {"id": ciclo_ref.etapa_actual.id, "nombre": ciclo_ref.etapa_actual.nombre}
                if ciclo_ref.etapa_actual else None
            ),
            "etapa_inicio": ciclo_ref.etapa_inicio
        }, status=status.HTTP_200_OK)


class CicloCloseView(APIView):
    """
    Cierra un ciclo. POST body optional: {"fecha":"YYYY-MM-DD"}
    """
    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('parcelas', 'actualizar')]

    @extend_schema(
        tags=['ciclos'],
        summary='Cerrar ciclo',
        description='Marca un ciclo como cerrado. Body opcional: {"fecha":"YYYY-MM-DD"}. Requiere parcelas.actualizar.',
        request={'type': 'object', 'properties': {'fecha': {'type': 'string', 'format': 'date'}}},
        responses={200: OpenApiExample('Cerrar', value={"closed": True, "ciclo_id": 1, "estado": "cerrado", "fecha_cierre": "2025-10-28"})}
    )
    def post(self, request, pk):
        from rest_framework.exceptions import PermissionDenied, NotFound
        try:
            ciclo = Ciclo.objects.select_related('parcela__usuario').get(pk=pk)
        except Ciclo.DoesNotExist:
            raise NotFound("Ciclo no encontrado.")

        r = role_name(request.user)
        if r not in ['superadmin', 'administrador', 'tecnico'] and ciclo.parcela.usuario_id != request.user.id:
            raise PermissionDenied("No puede cerrar ciclos de otra persona.")

        fecha = request.data.get('fecha')
        if fecha:
            try:
                fecha = date.fromisoformat(fecha)
            except Exception:
                return Response({"detail": "Formato de fecha inválido. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        closed = ciclo.close(fecha=fecha)
        return Response({
            "closed": closed,
            "ciclo_id": ciclo.id,
            "estado": ciclo.estado,
            "fecha_cierre": ciclo.fecha_cierre
        }, status=status.HTTP_200_OK)

class CicloAdvanceActiveView(APIView):
    """
    Avanza la etapa del ciclo ACTIVO del usuario autenticado.
    POST body optional: {"force": true}
    Admin/tecnico/superadmin puede pasar ?parcela_id=; agricultor avanza su ciclo activo.
    """
    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('parcelas', 'actualizar')]

    @extend_schema(
        tags=['ciclos'],
        summary='Avanzar etapa del ciclo activo (usuario autenticado)',
        description='Avanza el ciclo ACTIVO del usuario (o admin con ?parcela_id). Requiere parcelas.actualizar.',
        request={'type': 'object', 'properties': {'force': {'type': 'boolean'}}},
        responses={200: OpenApiExample('AvanceActivo', value={"advanced": True, "ciclo_id": 1})}
    )
    def post(self, request):
        from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

        parcela_id = request.query_params.get('parcela_id')
        user = request.user
        r = role_name(user)

        qs = Ciclo.objects.select_related('parcela__usuario', 'etapa_actual', 'etapa_actual__variedad')
        if r in ['superadmin', 'administrador', 'tecnico']:
            if parcela_id:
                try:
                    parcela_id = int(parcela_id)
                except Exception:
                    return Response({"detail": "parcela_id inválido."}, status=status.HTTP_400_BAD_REQUEST)
                ciclo = qs.filter(parcela_id=parcela_id, estado='activo').order_by('-created_at').first()
            else:
                ciclo = qs.filter(estado='activo').order_by('-created_at').first()
        else:
            ciclo = qs.filter(parcela__usuario=user, estado='activo').order_by('-created_at').first()

        if not ciclo:
            raise NotFound("No se encontró un ciclo activo para avanzar.")

        if r not in ['superadmin', 'administrador', 'tecnico'] and ciclo.parcela.usuario_id != user.id:
            raise PermissionDenied("No puede modificar ciclos de otra persona.")

        force = bool(request.data.get('force'))
        if force:
            etapa_actual = ciclo.etapa_actual
            if not etapa_actual:
                raise ValidationError({"etapa_actual": "El ciclo no tiene etapa actual para avanzar."})
            siguiente = Etapa.objects.filter(
                variedad=etapa_actual.variedad,
                orden__gt=etapa_actual.orden,
                activo=True
            ).order_by('orden').first()
            if not siguiente:
                return Response({"advanced": False, "detail": "No existe una siguiente etapa activa."}, status=status.HTTP_200_OK)
            ciclo.etapa_actual = siguiente
            start = timezone.now().date() if not ciclo.etapa_inicio else ciclo.etapa_inicio
            ciclo.etapa_inicio = start
            ciclo.save(update_fields=['etapa_actual', 'etapa_inicio', 'updated_at'])
            advanced = True
        else:
            advanced = ciclo.advance_etapa_if_needed()

        ciclo_ref = Ciclo.objects.select_related('etapa_actual').get(pk=ciclo.pk)
        return Response({
            "advanced": advanced,
            "ciclo_id": ciclo_ref.id,
            "etapa_actual": ({"id": ciclo_ref.etapa_actual.id, "nombre": ciclo_ref.etapa_actual.nombre} if ciclo_ref.etapa_actual else None),
            "etapa_inicio": ciclo_ref.etapa_inicio
        }, status=status.HTTP_200_OK)
    
    
# ----------------------------------------
# Parcela endpoints (list/create + detail)
# ----------------------------------------
@extend_schema_view(
    get=extend_schema(tags=['parcelas'], summary='Listar parcelas', responses={200: ParcelaReadSerializer(many=True)}),
    post=extend_schema(
        tags=['parcelas'],
        summary='Crear parcela',
        description='Crear parcela. Si no se pasa "usuario" se asigna request.user. Requiere parcelas.crear.',
        request=ParcelaCreateSerializer,
        responses={201: ParcelaReadSerializer},
        examples=[OpenApiExample('Crear parcela', value={"nombre":"Parcela Demo","ubicacion":"Valle","tamano_hectareas":5.0}, request_only=True)]
    )
)
class ParcelaListCreateView(generics.ListCreateAPIView):
    """
    Lista parcelas visibles para el usuario y permite crear nuevas parcelas.
    """
    queryset = Parcela.objects.select_related('usuario').order_by('nombre')
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # aceptar multipart/form-data y application/json

    def get_serializer_class(self):
        return ParcelaReadSerializer if self.request.method == 'GET' else ParcelaCreateSerializer

    def get_permissions(self):
        op = 'ver' if self.request.method == 'GET' else 'crear'
        return [permissions.IsAuthenticated(), HasOperationPermission('parcelas', op)]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'parcelas', 'ver'):
            return Parcela.objects.none()
        r = role_name(user)
        qs = self.queryset
        if r in ['superadmin', 'administrador', 'tecnico']:
            return qs
        return qs.filter(usuario=user)

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied
        user = self.request.user
        provided_user = serializer.validated_data.get('usuario', None)

        r = role_name(user)
        if provided_user:
            if r in ['superadmin', 'administrador']:
                parcel = serializer.save()
            else:
                if getattr(provided_user, 'id', None) != user.id:
                    raise PermissionDenied("No tiene permiso para crear una parcela para otro usuario.")
                parcel = serializer.save(usuario=user)
        else:
            parcel = serializer.save(usuario=user)
        # Nota: ParcelaCreateSerializer.create ya procesa request.FILES['imagen'] si existe

@extend_schema_view(
    get=extend_schema(tags=['parcelas'], summary='Detalle de parcela', responses={200: ParcelaReadSerializer}),
    put=extend_schema(tags=['parcelas'], summary='Actualizar parcela', request=ParcelaUpdateSerializer, responses={200: ParcelaReadSerializer}),
    patch=extend_schema(tags=['parcelas'], summary='Actualizar parcialmente parcela', request=ParcelaUpdateSerializer, responses={200: ParcelaReadSerializer}),
    delete=extend_schema(tags=['parcelas'], summary='Eliminar parcela', responses={204: None})
)
class ParcelaDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Recuperar / actualizar / eliminar una parcela.
    Permisos controlados por módulo 'parcelas'.
    """
    queryset = Parcela.objects.select_related('usuario')
    serializer_class = ParcelaReadSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # aceptar JSON en update

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ParcelaReadSerializer
        if self.request.method in ['PUT', 'PATCH']:
            return ParcelaUpdateSerializer
        return ParcelaReadSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), HasOperationPermission('parcelas', 'ver')]
        if self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), HasOperationPermission('parcelas', 'actualizar')]
        if self.request.method == 'DELETE':
            return [permissions.IsAuthenticated(), HasOperationPermission('parcelas', 'eliminar')]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if not tiene_permiso(user, 'parcelas', 'ver'):
            return Parcela.objects.none()
        r = role_name(user)
        qs = self.queryset
        if r in ['superadmin', 'administrador', 'tecnico']:
            return qs
        return qs.filter(usuario=user)

    def perform_update(self, serializer):
        # permiso y validaciones existentes
        user = self.request.user
        instancia = self.get_object()
        r = role_name(user)
        if r not in ['superadmin', 'administrador', 'tecnico'] and instancia.usuario_id != user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No puede actualizar una parcela que no es suya.")
        parcela = serializer.save()

        # si se subió campo 'imagen' en multipart update, subirlo a Cloudinary y guardar en parcela.imagen_url
        file_obj = self.request.FILES.get('imagen')
        if file_obj:
            try:
                res = cloudinary.uploader.upload(
                    file_obj,
                    folder=f"agro_ai/parcels_preview/{parcela.id}",
                    resource_type="image",
                    use_filename=True,
                    unique_filename=True
                )
                parcela.imagen_url = res.get('secure_url')
                parcela.imagen_public_id = res.get('public_id')
                parcela.save(update_fields=['imagen_url', 'imagen_public_id', 'updated_at'])
            except Exception:
                pass

    def perform_destroy(self, instance):
        user = self.request.user
        r = role_name(user)
        if r not in ['superadmin', 'administrador', 'tecnico'] and instance.usuario_id != user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No puede eliminar una parcela que no es suya.")
        instance.delete()


@extend_schema_view(
    post=extend_schema(
        tags=['parcelas'],
        summary='Crear parcela (usuario autenticado)',
        description=(
            "Crea una parcela y la asigna al usuario autenticado. "
            "No es necesario enviar 'usuario' en el body; será ignorado si se envía."
        ),
        request=ParcelaCreateSerializer,
        responses={201: ParcelaReadSerializer}
    )
)
class ParcelaCreateOwnView(generics.CreateAPIView):
    """
    Crear parcela asignada automáticamente al usuario autenticado.
    No se considera el campo 'usuario' del payload: siempre se usa request.user.
    Requiere permisos: parcelas.crear
    """
    serializer_class = ParcelaCreateSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('parcelas', 'crear')]

    def post(self, request, *args, **kwargs):
        # delegar a DRF para comportamiento estándar (no requerir 'usuario' en el body)
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        # Forzar owner = request.user siempre (doble garantía)
        serializer.save(usuario=self.request.user)

# ----------------------------------------
# ParcelaImage endpoints (list/create, detail, delete, set-as-parcela-image)
# ----------------------------------------
@extend_schema_view(
    get=extend_schema(tags=['imagenes'], summary='Listar imágenes de una parcela', responses={200: ParcelaImageSerializer(many=True)}),
    post=extend_schema(
        tags=['imagenes'],
        summary='Subir imagen para análisis',
        description='Enviar multipart/form-data con campo "image". Requiere parcelas.actualizar.',
        request=None,
        responses={201: ParcelaImageSerializer}
    )
)
class ParcelaImageListCreateView(generics.ListCreateAPIView):
    """
    GET: lista imágenes asociadas a una parcela (requiere 'parcelas.ver')
    POST: sube una imagen (form-data field 'image') a Cloudinary y crea ParcelaImage (requiere 'parcelas.actualizar')
    """
    serializer_class = ParcelaImageSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), HasOperationPermission('parcelas', 'ver')]
        return [permissions.IsAuthenticated(), HasOperationPermission('parcelas', 'actualizar')]

    def _get_parcela_or_403(self):
        from rest_framework.exceptions import PermissionDenied, NotFound
        parcela_id = self.kwargs.get('parcela_id')
        try:
            parcela = Parcela.objects.get(pk=parcela_id)
        except Parcela.DoesNotExist:
            raise NotFound("Parcela no encontrada.")
        r = role_name(self.request.user)
        if r not in ['superadmin', 'administrador', 'tecnico'] and parcela.usuario_id != self.request.user.id:
            raise PermissionDenied("No puede acceder a imágenes de una parcela que no es suya.")
        return parcela

    def get_queryset(self):
        parcela = self._get_parcela_or_403()
        return ParcelaImage.objects.filter(parcela=parcela).order_by('-created_at')

    def perform_create(self, serializer):
        # NO se usa: create via post() override
        return super().perform_create(serializer)

    def post(self, request, parcela_id, *args, **kwargs):
        from rest_framework.exceptions import NotFound, PermissionDenied
        parcela = self._get_parcela_or_403()

        # permiso adicional: requiere 'parcelas.actualizar'
        if not tiene_permiso(request.user, 'parcelas', 'actualizar'):
            raise PermissionDenied("No tiene permiso para subir imágenes.")

        file_obj = request.FILES.get('image')
        if not file_obj:
            return Response({'detail': 'Archivo "image" requerido (form-data).'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            res = cloudinary.uploader.upload(
                file_obj,
                folder=f"agro_ai/parcels_images/{parcela.id}",
                resource_type="image",
                use_filename=True,
                unique_filename=True
            )
        except Exception as e:
            return Response({'detail': 'Error al subir a Cloudinary', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        image = ParcelaImage.objects.create(
            parcela=parcela,
            image_url=res.get('secure_url'),
            public_id=res.get('public_id'),
            filename=res.get('original_filename') or getattr(file_obj, 'name', None),
            uploaded_by=request.user
        )
        serializer = self.get_serializer(image, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ParcelaImageDetailView(generics.RetrieveDestroyAPIView):
    """
    GET: detalle de una imagen
    DELETE: borrar imagen (también intenta borrar en Cloudinary) — requiere 'parcelas.actualizar'
    """
    serializer_class = ParcelaImageSerializer
    lookup_url_kwarg = 'image_id'

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), HasOperationPermission('parcelas', 'ver')]
        return [permissions.IsAuthenticated(), HasOperationPermission('parcelas', 'actualizar')]

    def get_queryset(self):
        # restringir según permisos/propiedad
        user = self.request.user
        if not tiene_permiso(user, 'parcelas', 'ver'):
            return ParcelaImage.objects.none()
        r = role_name(user)
        qs = ParcelaImage.objects.select_related('parcela__usuario')
        if r in ['superadmin', 'administrador', 'tecnico']:
            return qs
        return qs.filter(parcela__usuario=user)

    def perform_destroy(self, instance):
        # intentar borrar en Cloudinary si public_id existe
        try:
            if instance.public_id:
                cloudinary.uploader.destroy(instance.public_id, invalidate=True, resource_type='image')
        except Exception:
            # ignorar error de borrado remoto para no bloquear eliminación local
            pass
        instance.delete()




