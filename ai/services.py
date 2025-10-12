from .models import AIIntegration
from parcels.models import Parcela
#from sensors.mongo import get_readings_summary  # Supón que tienes esta función
import requests

def get_active_ai_config():
    return AIIntegration.objects.filter(activo=True).first()

def chat_with_ai(prompt, context=None):
    config = get_active_ai_config()
    if not config:
        return "No hay proveedor IA activo configurado."
    if config.provider == "ollama":
        # Aquí iría tu integración real con Ollama
        return ollama_chat(prompt, context, config.endpoint)
    elif config.provider == "gemini":
        # Aquí iría tu integración real con Gemini
        return gemini_chat(prompt, context, config.api_key)
    elif config.provider == "anthropic":
        # Aquí iría tu integración real con Anthropic
        return anthropic_chat(prompt, context, config.api_key)
    else:
        return "Proveedor IA no soportado."

# Ejemplo de función stub para Ollama
def ollama_chat(prompt, context, endpoint):
    payload = {
        "model": "llama3.1",
        "prompt": prompt if not context else f"{context}\n{prompt}",
        "stream": False,
        "options": {
            "temperature": 0.3,
            "top_p": 0.8
        }
    }
    response = requests.post(f"{endpoint}/api/generate", json=payload, timeout=60)
    if response.status_code == 200:
        return response.json().get("response", "")
    return f"Error Ollama: {response.text}"

def gemini_chat(prompt, context, api_key):
    # Implementa aquí la llamada real a Gemini
    return f"[Gemini] {prompt}"

def anthropic_chat(prompt, context, api_key):
    # Implementa aquí la llamada real a Anthropic
    return f"[Anthropic] {prompt}"

def get_context(usuario_id, parcela_id, consulta, prompt=None):
    # Solo busca contexto si es "dia", "semana" o "todas"
    if consulta in ["dia", "semana", "todas"]:
        try:
            resumen = get_readings_summary(parcela_id, period=consulta)
            if not resumen:
                return "No hay datos de sensores disponibles para esta parcela y periodo."
            return resumen
        except Exception:
            return "No hay datos de sensores disponibles para esta parcela y periodo."
    # Si no es contexto de datos, pero pregunta sobre la fresa, responde normalmente
    if prompt and "fresa" in prompt.lower():
        return None  # La IA responderá solo con el prompt, sin contexto adicional
    return "No se encontró contexto relevante."

def get_readings_summary(parcela_id, period="dia"):
    # Stub temporal: simula datos agregados
    return f"Resumen simulado para parcela {parcela_id} en periodo {period}."