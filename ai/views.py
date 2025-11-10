from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from .serializers import ChatRequestSerializer
from .services import chat_with_ai, get_context
from .models import AIIntegration
from .serializers import AIIntegrationSerializer
from drf_spectacular.utils import extend_schema, OpenApiExample, extend_schema_view
from rest_framework import viewsets, permissions

def detectar_tipo_consulta(prompt):
    texto = prompt.lower()
    if "semana" in texto:
        return "semana"
    elif "hoy" in texto or "día" in texto:
        return "dia"
    elif "todas" in texto or "todas mis parcelas" in texto:
        return "todas"
    # Si no se detecta, pregunta a la IA
    tipo = chat_with_ai(
        f"Clasifica esta consulta: '{prompt}'. Responde solo con: dia, semana, todas.",
        context=None
    )
    # Normaliza la respuesta de la IA
    tipo = tipo.strip().lower()
    if tipo in ["dia", "semana", "todas"]:
        return tipo
    return "dia"  # por defecto

@extend_schema(
    tags=['IA'],
    summary='Chat con IA',
    description='Permite enviar un mensaje (prompt) a la IA y obtener una respuesta contextualizada según el usuario y la parcela.',
    request=ChatRequestSerializer,
    responses={
        200: OpenApiExample(
            'Respuesta exitosa',
            value={"respuesta": "La parcela está en buen estado hoy."}
        ),
        400: OpenApiExample(
            'Error',
            value={"detail": "prompt requerido"}
        )
    }
)
class AIChatView(APIView):
    serializer_class = ChatRequestSerializer

    def post(self, request):
        s = self.serializer_class(data=request.data)
        s.is_valid(raise_exception=True)
        prompt = s.validated_data["prompt"]
        parcela_id = s.validated_data.get("parcela_id")
        usuario_id = getattr(request.user, "id", None)

        consulta = detectar_tipo_consulta(prompt)
        contexto = get_context(usuario_id, parcela_id, consulta)
        respuesta = chat_with_ai(prompt, contexto)
        return Response({"respuesta": respuesta}, status=status.HTTP_200_OK)

@extend_schema_view(
    list=extend_schema(
        tags=['IA'],
        summary='Listar integraciones IA',
        description='Devuelve la lista de integraciones configuradas para la IA.',
        responses=AIIntegrationSerializer(many=True)
    ),
    retrieve=extend_schema(
        tags=['IA'],
        summary='Detalle de integración IA',
        description='Devuelve el detalle de una integración específica de IA.',
        responses=AIIntegrationSerializer
    ),
    create=extend_schema(
        tags=['IA'],
        summary='Crear integración IA',
        description='Permite crear una nueva integración para la IA.',
        request=AIIntegrationSerializer,
        responses=AIIntegrationSerializer
    ),
    update=extend_schema(
        tags=['IA'],
        summary='Actualizar integración IA',
        description='Permite actualizar una integración existente de IA.',
        request=AIIntegrationSerializer,
        responses=AIIntegrationSerializer
    ),
    partial_update=extend_schema(
        tags=['IA'],
        summary='Actualizar parcialmente integración IA',
        description='Permite actualizar parcialmente una integración de IA.',
        request=AIIntegrationSerializer,
        responses=AIIntegrationSerializer
    ),
    destroy=extend_schema(
        tags=['IA'],
        summary='Eliminar integración IA',
        description='Elimina una integración de IA.'
    ),
)
class AIIntegrationViewSet(viewsets.ModelViewSet):
    queryset = AIIntegration.objects.all()
    serializer_class = AIIntegrationSerializer
    permission_classes = [permissions.IsAdminUser]