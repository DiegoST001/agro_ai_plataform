from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings

from .services.anthropic_client import AnthropicClient

class AIChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Simple chat endpoint using the global AI provider (Anthropic Claude Sonnet 4 by default).
        Body:
        { "messages": [ {"role": "user", "content": "..."}, ... ], "max_tokens": 512, "temperature": 0.7 }
        """
        data = request.data or {}
        messages = data.get('messages') or []
        if not isinstance(messages, list) or not messages:
            return Response({"detail": "messages (list) es requerido."}, status=400)

        max_tokens = int(data.get('max_tokens') or 512)
        temperature = float(data.get('temperature') or 0.7)

        if settings.AI_PROVIDER == 'anthropic':
            client = AnthropicClient()
        else:
            return Response({"detail": f"AI_PROVIDER no soportado: {settings.AI_PROVIDER}"}, status=400)

        try:
            result = client.chat(messages, max_tokens=max_tokens, temperature=temperature)
            return Response({
                "model": settings.ANTHROPIC_MODEL,
                "provider": settings.AI_PROVIDER,
                "text": result.get('text', ''),
                "raw": result.get('raw', {}),
            })
        except Exception as e:
            return Response({"detail": str(e)}, status=502)
