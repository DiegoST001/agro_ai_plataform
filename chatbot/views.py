from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiExample
import os
import tempfile
from .serializers import (
    ChatRequestSerializer, 
    ChatResponseSerializer,
    ChatMessageSerializer,
    CropDataSerializer
)
from .services import process_chatbot_message, get_chat_history, get_or_create_crop_data, transcribe_audio_with_whisper
from .models import ChatMessage


@extend_schema(
    tags=['Chatbot'],
    summary='Chat con AgroNix - Asistente IA para Fresas',
    description=(
        "Endpoint principal del chatbot AgroNix.\n\n"
        "Envía un mensaje y recibe:\n"
        "- Respuesta inteligente del bot\n"
        "- Datos actualizados del cultivo (si aplica)\n"
        "- Lista de tareas creadas automáticamente (si aplica)\n\n"
        "El bot puede ayudar con:\n"
        "• Análisis de datos del cultivo\n"
        "• Recomendaciones de riego\n"
        "• Planes de fertilización\n"
        "• Control de plagas\n"
        "• Programación de tareas\n"
        "• Resumen del dashboard\n\n"
        "**No requiere autenticación** para facilitar acceso desde Flutter."
    ),
    request=ChatRequestSerializer,
    responses={
        200: ChatResponseSerializer,
        400: OpenApiExample(
            'Error de validación',
            value={"error": "El campo 'message' es requerido"}
        )
    },
    examples=[
        OpenApiExample(
            'Consulta de datos',
            value={"message": "Muéstrame los datos del cultivo", "username": "agri01"},
            request_only=True
        ),
        OpenApiExample(
            'Consulta de riego',
            value={"message": "¿Necesito regar?", "username": "agri01"},
            request_only=True
        ),
        OpenApiExample(
            'Respuesta exitosa',
            value={
                "response": "✅ La humedad del suelo está óptima en 55%...",
                "crop_data": {
                    "temperature_air": 22.5,
                    "humidity_air": 70.0,
                    "humidity_soil": 55.0,
                    "conductivity_ec": 0.95,
                    "temperature_soil": 18.5,
                    "solar_radiation": 650.0,
                    "pest_risk": "Bajo",
                    "last_updated": "2024-01-15T10:30:00Z"
                },
                "tasks_created": []
            },
            response_only=True
        )
    ]
)
class ChatbotView(APIView):
    """
    Vista principal del chatbot - No requiere autenticación
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = ChatRequestSerializer
    
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {"error": "El campo 'message' es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message = serializer.validated_data.get('message')
        username = serializer.validated_data.get('username', 'Usuario')
        
        if not message or not message.strip():
            return Response(
                {"error": "El mensaje no puede estar vacío"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Procesar mensaje y generar respuesta
            result = process_chatbot_message(message, username)
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Error procesando mensaje: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    tags=['Chatbot'],
    summary='Historial de chat del usuario',
    description=(
        "Obtiene el historial de mensajes de chat de un usuario específico.\n\n"
        "Query params:\n"
        "- username (required): nombre del usuario\n"
        "- limit (optional): número máximo de mensajes (default: 50)\n\n"
        "Retorna los mensajes ordenados por fecha (más recientes primero)."
    ),
    responses={
        200: ChatMessageSerializer(many=True),
        400: OpenApiExample(
            'Error',
            value={"error": "El parámetro 'username' es requerido"}
        )
    }
)
class ChatHistoryView(APIView):
    """
    Vista para obtener historial de chat - No requiere autenticación
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        username = request.query_params.get('username')
        limit = int(request.query_params.get('limit', 50))
        
        if not username:
            return Response(
                {"error": "El parámetro 'username' es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            messages = get_chat_history(username, limit)
            serializer = ChatMessageSerializer(messages, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Error obteniendo historial: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    tags=['Chatbot'],
    summary='Datos actuales del cultivo',
    description=(
        "Obtiene los datos más recientes del cultivo de fresas.\n\n"
        "Retorna parámetros como:\n"
        "- Temperatura del aire y suelo\n"
        "- Humedad del aire y suelo\n"
        "- Conductividad eléctrica\n"
        "- Radiación solar\n"
        "- Riesgo de plagas\n\n"
        "Los datos se generan/actualizan automáticamente cada hora."
    ),
    responses={
        200: CropDataSerializer
    }
)
class CropDataView(APIView):
    """
    Vista para obtener datos del cultivo - No requiere autenticación
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        try:
            crop_data = get_or_create_crop_data()
            serializer = CropDataSerializer(crop_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Error obteniendo datos del cultivo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    tags=['Chatbot'],
    summary='Limpiar historial de chat',
    description=(
        "Elimina todo el historial de mensajes de un usuario.\n\n"
        "Body params (JSON):\n"
        "- username (required): nombre del usuario\n\n"
        "⚠️ Esta acción no se puede deshacer."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "example": "agri01"}
            },
            "required": ["username"]
        }
    },
    responses={
        200: OpenApiExample(
            'Éxito',
            value={"message": "Historial eliminado", "deleted_count": 25}
        ),
        400: OpenApiExample(
            'Error',
            value={"error": "El campo 'username' es requerido"}
        )
    }
)
class ClearChatHistoryView(APIView):
    """
    Vista para limpiar historial de chat - No requiere autenticación
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        
        if not username:
            return Response(
                {"error": "El campo 'username' es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            deleted_count, _ = ChatMessage.objects.filter(username=username).delete()
            return Response(
                {
                    "message": "Historial eliminado correctamente",
                    "deleted_count": deleted_count
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"Error eliminando historial: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    tags=['Chatbot'],
    summary='Chat por voz con AgroNix',
    description=(
        "Endpoint de voz del chatbot AgroNix.\n\n"
        "Envía un archivo de audio y recibe:\n"
        "- Texto transcrito de tu voz\n"
        "- Respuesta inteligente del bot\n"
        "- Datos actualizados del cultivo (si aplica)\n"
        "- Lista de tareas creadas automáticamente (si aplica)\n\n"
        "**Formatos soportados:** .m4a, .mp3, .wav, .ogg, .webm\n"
        "**Transcripción:** OpenAI Whisper (español optimizado)\n\n"
        "**No requiere autenticación** para facilitar acceso desde Flutter."
    ),
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'audio': {'type': 'string', 'format': 'binary'},
                'username': {'type': 'string'}
            }
        }
    },
    responses={
        200: OpenApiExample(
            'Respuesta exitosa',
            value={
                "transcribed_text": "Muéstrame los datos del cultivo",
                "response": "📊 **Estado actual de tu cultivo:**\n...",
                "crop_data": {"temperature_air": 22.5, "humidity_air": 68.2},
                "tasks_created": []
            }
        ),
        400: OpenApiExample(
            'Error de validación',
            value={"error": "No se recibió archivo de audio"}
        )
    }
)
class VoiceChatView(APIView):
    """Vista para procesar mensajes de voz del chatbot"""
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        # Validar que se recibió el archivo de audio
        audio_file = request.FILES.get('audio')
        username = request.data.get('username', 'Usuario')
        
        if not audio_file:
            return Response(
                {"error": "No se recibió archivo de audio"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear archivo temporal para guardar el audio
        temp_file = None
        try:
            # Guardar audio en archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.name)[1]) as temp_file:
                for chunk in audio_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name
            
            # Transcribir audio con Whisper
            transcribed_text = transcribe_audio_with_whisper(temp_file_path)
            
            if not transcribed_text:
                return Response(
                    {"error": "No se pudo transcribir el audio. Intenta hablar más claro o verifica el formato del archivo."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Procesar mensaje transcrito como texto normal
            result = process_chatbot_message(transcribed_text, username)
            
            # Agregar texto transcrito a la respuesta
            result['transcribed_text'] = transcribed_text
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Error procesando audio: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        finally:
            # Limpiar archivo temporal
            if temp_file and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    print(f"Error eliminando archivo temporal: {str(e)}")
