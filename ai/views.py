from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from ai.services.ollama import chat
from drf_spectacular.utils import extend_schema
from .serializers import OllamaChatRequest, OllamaChatResponse

class OllamaChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["AI / Ollama"],
        request=OllamaChatRequest,
        responses={200: OllamaChatResponse, 400: None, 502: None, 500: None},
        summary="Chat con Ollama",
        description="Invoca el binario de Ollama y retorna el texto generado.",
    )
    def post(self, request):
        prompt = request.data.get("prompt")
        if not prompt:
            return Response({"detail": "prompt es requerido"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            text = chat(prompt)
            return Response({"text": text}, status=status.HTTP_200_OK)
        except FileNotFoundError:
            return Response({"detail": "ollama no disponible"}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as ex:
            return Response({"detail": str(ex)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)