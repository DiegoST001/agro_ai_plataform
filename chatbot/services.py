import random
import os
import tempfile
from datetime import datetime, timedelta
from django.utils import timezone
from .models import CropData, ChatMessage
from ai.services import chat_with_ai, get_active_ai_config

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


def get_or_create_crop_data():
    """
    Obtiene los datos más recientes del cultivo o crea datos simulados
    si no existen o son muy antiguos
    """
    try:
        crop_data = CropData.objects.latest('last_updated')
        # Si los datos tienen más de 1 hora, actualizar
        if timezone.now() - crop_data.last_updated > timedelta(hours=1):
            crop_data = generate_crop_data()
    except CropData.DoesNotExist:
        crop_data = generate_crop_data()
    
    return crop_data


def generate_crop_data():
    """Genera datos simulados realistas para cultivo de fresas San Andreas"""
    # Valores óptimos para fresas San Andreas con variación
    temperature_air = round(random.uniform(18.0, 27.0), 1)
    humidity_air = round(random.uniform(55.0, 85.0), 1)
    humidity_soil = round(random.uniform(30.0, 70.0), 1)
    conductivity_ec = round(random.uniform(0.6, 1.4), 2)
    temperature_soil = round(random.uniform(13.0, 27.0), 1)
    solar_radiation = round(random.uniform(250.0, 900.0), 1)
    
    # Determinar riesgo de plagas basado en condiciones
    if temperature_air > 25 and humidity_air > 75:
        pest_risk = 'Alto'
    elif temperature_air > 22 and humidity_air > 65:
        pest_risk = 'Moderado'
    else:
        pest_risk = 'Bajo'
    
    crop_data = CropData.objects.create(
        temperature_air=temperature_air,
        humidity_air=humidity_air,
        humidity_soil=humidity_soil,
        conductivity_ec=conductivity_ec,
        temperature_soil=temperature_soil,
        solar_radiation=solar_radiation,
        pest_risk=pest_risk,
        last_updated=timezone.now()
    )
    
    return crop_data


def process_chatbot_message(message, username=''):
    """
    Procesa el mensaje del usuario y genera una respuesta inteligente
    utilizando IA si está configurada, o respuestas predefinidas
    """
    message_lower = message.lower()
    
    # Guardar mensaje del usuario
    ChatMessage.objects.create(
        username=username or 'Usuario',
        message=message,
        is_user=True,
        timestamp=timezone.now()
    )
    
    # Obtener datos del cultivo
    crop_data = get_or_create_crop_data()
    crop_data_dict = {
        'temperature_air': crop_data.temperature_air,
        'humidity_air': crop_data.humidity_air,
        'humidity_soil': crop_data.humidity_soil,
        'conductivity_ec': crop_data.conductivity_ec,
        'temperature_soil': crop_data.temperature_soil,
        'solar_radiation': crop_data.solar_radiation,
        'pest_risk': crop_data.pest_risk,
        'last_updated': crop_data.last_updated.isoformat()
    }
    
    tasks_created = []
    
    # Detectar intención del mensaje
    if any(keyword in message_lower for keyword in ['hola', 'buenos días', 'buenas tardes', 'buenas noches', 'qué tal', 'hey', 'hi']):
        response = generate_greeting_response(username, crop_data)
        
    elif any(keyword in message_lower for keyword in ['ayuda', 'ayúdame', 'qué puedes hacer', 'cómo funciona', 'comandos']):
        response = generate_help_response(username)
        
    elif any(keyword in message_lower for keyword in ['datos', 'cultivo', 'sensor', 'temperatura', 'humedad', 'parámetro', 'información', 'estado']):
        response = generate_crop_analysis_response(crop_data, username)
        
    elif any(keyword in message_lower for keyword in ['riego', 'regar', 'agua', 'humedad del suelo', 'secar', 'seco']):
        response, task = generate_irrigation_response(crop_data, username)
        if task:
            tasks_created.append(task)
            
    elif any(keyword in message_lower for keyword in ['fertiliz', 'nutriente', 'abono', 'npk', 'nitrogeno', 'fosforo', 'potasio']):
        response, task = generate_fertilization_response(crop_data, username)
        if task:
            tasks_created.append(task)
            
    elif any(keyword in message_lower for keyword in ['plaga', 'enfermedad', 'control', 'prevención', 'araña', 'trips', 'hongo']):
        response, task = generate_pest_response(crop_data, username)
        if task:
            tasks_created.append(task)
            
    elif any(keyword in message_lower for keyword in ['tarea', 'programar', 'calendario', 'agendar', 'crear tarea', 'añadir']):
        response, new_tasks = generate_task_creation_response(message, username)
        tasks_created.extend(new_tasks)
        
    elif any(keyword in message_lower for keyword in ['dashboard', 'resumen', 'estadística', 'producción', 'kpi']):
        response = generate_dashboard_summary(username)
        
    elif any(keyword in message_lower for keyword in ['gracias', 'thank', 'perfecto', 'excelente', 'genial', 'ok']):
        response = generate_thanks_response(username)
        
    elif any(keyword in message_lower for keyword in ['problema', 'error', 'falla', 'no funciona', 'ayuda urgente']):
        response = generate_problem_response(username, crop_data)
        
    else:
        # Intentar usar IA si está configurada, si no, dar respuesta contextual
        response = generate_ai_response(message, crop_data, username)
    
    # Guardar respuesta del bot
    ChatMessage.objects.create(
        username=username or 'Usuario',
        message=response,
        is_user=False,
        timestamp=timezone.now()
    )
    
    return {
        'response': response,
        'crop_data': crop_data_dict,
        'tasks_created': tasks_created
    }


def generate_greeting_response(username, crop_data):
    """Genera respuesta de saludo variada según el estado del cultivo"""
    import random
    
    greetings = [
        f"¡Hola {username}! 👋 ¿En qué puedo ayudarte con tus fresas hoy?",
        f"¡Buenos días {username}! 🌱 Estoy aquí para ayudarte con tu cultivo.",
        f"¡Hola de nuevo {username}! ¿Cómo va tu cultivo de fresas?",
        f"¡Saludos {username}! 🍓 ¿Qué necesitas saber sobre tus fresas?",
    ]
    
    greeting = random.choice(greetings)
    
    # Agregar info rápida del estado
    if crop_data.humidity_soil < 35:
        greeting += f"\n\n⚠️ **Nota importante:** Tu humedad del suelo está en {crop_data.humidity_soil}%, considera regar pronto."
    elif crop_data.pest_risk == 'Alto':
        greeting += f"\n\n⚠️ **Alerta:** Hay riesgo alto de plagas. Revisa tus plantas."
    else:
        greeting += f"\n\n✅ Tu cultivo está en buen estado general."
    
    return greeting


def generate_help_response(username):
    """Genera respuesta de ayuda"""
    return f"""¡Claro {username}! Puedo ayudarte con muchas cosas 🤓

**Preguntas que puedes hacer:**

📊 **Datos del cultivo:**
• "Muéstrame los datos del cultivo"
• "¿Cómo está la temperatura?"
• "Dame información de sensores"

💧 **Riego:**
• "¿Necesito regar?"
• "¿Cuándo debo regar?"
• "La tierra está seca"

🌿 **Fertilización:**
• "¿Necesito fertilizar?"
• "¿Qué nutrientes necesito?"
• "Dame plan de fertilización"

🐛 **Plagas:**
• "¿Hay plagas?"
• "Riesgo de enfermedades"
• "Cómo prevenir plagas"

📅 **Tareas:**
• "Programa un riego"
• "Crea tarea de poda"
• "Agenda fertilización"

📊 **Estadísticas:**
• "Muéstrame el dashboard"
• "Dame el resumen"
• "Estadísticas de producción"

¡Solo pregunta en lenguaje natural! 😊"""


def generate_thanks_response(username):
    """Genera respuesta de agradecimiento"""
    import random
    
    responses = [
        f"¡De nada {username}! 😊 Estoy aquí cuando me necesites.",
        f"¡Un placer ayudarte {username}! 🌱 Que tengas una excelente cosecha.",
        f"¡Para eso estoy {username}! 🍓 Si necesitas algo más, aquí estaré.",
        f"¡Feliz de ayudar {username}! 👍 ¡Mucho éxito con tus fresas!",
    ]
    
    return random.choice(responses)


def generate_problem_response(username, crop_data):
    """Genera respuesta para problemas urgentes"""
    response = f"⚠️ **Entiendo tu preocupación, {username}**. Déjame revisar los datos...\n\n"
    
    problems = []
    
    if crop_data.humidity_soil < 30:
        problems.append("🚨 **Crítico:** Humedad del suelo muy baja. Riega urgentemente.")
    elif crop_data.humidity_soil < 35:
        problems.append("⚠️ Humedad del suelo baja. Programa riego.")
    
    if crop_data.humidity_soil > 70:
        problems.append("⚠️ Exceso de agua. Suspende riego y mejora drenaje.")
    
    if crop_data.temperature_air > 28:
        problems.append("🌡️ Temperatura muy alta. Aumenta ventilación/sombreado.")
    elif crop_data.temperature_air < 15:
        problems.append("🌡️ Temperatura muy baja. Protege contra frío.")
    
    if crop_data.pest_risk == 'Alto':
        problems.append("🐛 Riesgo alto de plagas. Inspecciona y trata si es necesario.")
    
    if crop_data.conductivity_ec < 0.6:
        problems.append("⚡ Conductividad muy baja. Aumenta fertilización.")
    elif crop_data.conductivity_ec > 1.4:
        problems.append("⚡ Conductividad muy alta. Riega para lavar sales.")
    
    if problems:
        response += "**Problemas detectados:**\n"
        response += "\n".join(f"• {p}" for p in problems)
        response += "\n\n💡 **Recomendación:** Atiende primero los problemas críticos (🚨)."
    else:
        response += "**Buenas noticias:** No detecto problemas críticos en tus datos.\n\n"
        response += "Si tienes un problema específico, descríbelo con más detalle:\n"
        response += "• ¿Qué observas en las plantas?\n"
        response += "• ¿Desde cuándo ocurre?\n"
        response += "• ¿En qué parte del cultivo?"
    
    return response


def generate_crop_analysis_response(crop_data, username):
    """Genera análisis detallado de los datos del cultivo"""
    alerts = []
    
    # Análisis de temperatura del aire
    if crop_data.temperature_air < 18:
        alerts.append("🌡️ **Alerta:** Temperatura del aire baja. Considera protección contra heladas.")
    elif crop_data.temperature_air > 26:
        alerts.append("🌡️ **Alerta:** Temperatura del aire alta. Aumenta ventilación o sombreado.")
    
    # Análisis de humedad del aire
    if crop_data.humidity_air < 60:
        alerts.append("💧 **Alerta:** Humedad del aire baja. Considera nebulización.")
    elif crop_data.humidity_air > 80:
        alerts.append("💧 **Alerta:** Humedad del aire alta. Mejora la ventilación para prevenir hongos.")
    
    # Análisis de humedad del suelo
    if crop_data.humidity_soil < 35:
        alerts.append("🌱 **Urgente:** Humedad del suelo baja. Programa riego inmediato.")
    elif crop_data.humidity_soil > 65:
        alerts.append("🌱 **Alerta:** Humedad del suelo alta. Reduce frecuencia de riego.")
    
    # Análisis de conductividad
    if crop_data.conductivity_ec < 0.7:
        alerts.append("⚡ **Recomendación:** Conductividad baja. Aumenta fertilización.")
    elif crop_data.conductivity_ec > 1.2:
        alerts.append("⚡ **Alerta:** Conductividad alta. Reduce fertilización o riega para lavar sales.")
    
    greeting = f"¡Hola {username}! " if username else "¡Hola! "
    
    if alerts:
        response = greeting + "He analizado los datos de tu cultivo de fresas San Andreas 🍓\n\n"
        response += "**Estado actual:**\n"
        response += f"• Temperatura aire: {crop_data.temperature_air}°C\n"
        response += f"• Humedad aire: {crop_data.humidity_air}%\n"
        response += f"• Humedad suelo: {crop_data.humidity_soil}%\n"
        response += f"• Conductividad: {crop_data.conductivity_ec} dS/m\n"
        response += f"• Radiación solar: {crop_data.solar_radiation} W/m²\n"
        response += f"• Riesgo de plagas: {crop_data.pest_risk}\n\n"
        response += "**Alertas y recomendaciones:**\n"
        response += "\n".join(alerts)
    else:
        response = greeting + "¡Excelentes noticias! 🎉\n\n"
        response += "Todos los parámetros de tu cultivo de fresas San Andreas están en rangos óptimos:\n\n"
        response += f"✅ Temperatura aire: {crop_data.temperature_air}°C (ideal: 20-25°C)\n"
        response += f"✅ Humedad aire: {crop_data.humidity_air}% (ideal: 60-80%)\n"
        response += f"✅ Humedad suelo: {crop_data.humidity_soil}% (ideal: 35-65%)\n"
        response += f"✅ Conductividad: {crop_data.conductivity_ec} dS/m (ideal: 0.7-1.2)\n"
        response += f"✅ Radiación solar: {crop_data.solar_radiation} W/m²\n"
        response += f"✅ Riesgo de plagas: {crop_data.pest_risk}\n\n"
        response += "Mantén las condiciones actuales para una cosecha exitosa. 🌱"
    
    return response


def generate_irrigation_response(crop_data, username):
    """Genera recomendación de riego"""
    task = None
    
    if crop_data.humidity_soil < 35:
        response = f"🚨 **Acción Urgente**, {username}!\n\n"
        response += f"La humedad del suelo está en **{crop_data.humidity_soil}%**, por debajo del nivel crítico.\n\n"
        response += "**Recomendación:**\n"
        response += "• Riega inmediatamente con 15-20 L/m²\n"
        response += "• Monitorea en las próximas 2 horas\n"
        response += "• Verifica que el sistema de riego funcione correctamente\n\n"
        response += "He creado una tarea de riego urgente para ti. ✅"
        task = f"Riego urgente - Humedad suelo: {crop_data.humidity_soil}%"
        
    elif crop_data.humidity_soil < 45:
        response = f"💧 **Recomendación de Riego**, {username}\n\n"
        response += f"La humedad del suelo está en **{crop_data.humidity_soil}%**, ligeramente baja.\n\n"
        response += "**Plan de riego:**\n"
        response += "• Riega en las próximas 6 horas con 10-15 L/m²\n"
        response += "• Preferiblemente en horas de la mañana temprano\n"
        response += "• Evita riego en horas de máximo calor\n\n"
        response += "Tarea de riego programada. ✅"
        task = f"Programar riego - Humedad actual: {crop_data.humidity_soil}%"
        
    elif crop_data.humidity_soil > 65:
        response = f"⚠️ **Alerta de Exceso de Agua**, {username}\n\n"
        response += f"La humedad del suelo está en **{crop_data.humidity_soil}%**, demasiado alta.\n\n"
        response += "**Acciones recomendadas:**\n"
        response += "• Suspende riego por 24-48 horas\n"
        response += "• Mejora el drenaje si es posible\n"
        response += "• Monitorea para prevenir enfermedades fúngicas\n"
        response += "• Aumenta la ventilación\n\n"
        response += "Recuerda: El exceso de agua puede dañar las raíces. 🌱"
        
    else:
        response = f"✅ **Humedad Óptima**, {username}!\n\n"
        response += f"La humedad del suelo está en **{crop_data.humidity_soil}%**, nivel ideal.\n\n"
        response += "**Próximo riego:**\n"
        response += "• Programa para dentro de 12-24 horas\n"
        response += "• Cantidad: 8-12 L/m²\n"
        response += "• Horario recomendado: 6:00 - 8:00 AM\n\n"
        response += "Continúa con el plan de riego actual. 💧"
    
    return response, task


def generate_fertilization_response(crop_data, username):
    """Genera recomendación de fertilización"""
    task = None
    
    if crop_data.conductivity_ec < 0.7:
        response = f"🌿 **Plan de Fertilización**, {username}\n\n"
        response += f"La conductividad está en **{crop_data.conductivity_ec} dS/m**, por debajo del óptimo.\n\n"
        response += "**Recomendación de fertilización:**\n"
        response += "• NPK 12-6-12 o 15-5-15\n"
        response += "• Dosis: 50-75 kg/ha\n"
        response += "• Aplicación: En fertirrigación\n"
        response += "• Frecuencia: Cada 7-10 días\n\n"
        response += "**Nutrientes clave para fresas:**\n"
        response += "• Nitrógeno: Crecimiento vegetativo\n"
        response += "• Fósforo: Desarrollo de raíces y floración\n"
        response += "• Potasio: Calidad y sabor del fruto\n\n"
        response += "Tarea de fertilización creada. ✅"
        task = f"Fertilización NPK - EC actual: {crop_data.conductivity_ec} dS/m"
        
    elif crop_data.conductivity_ec > 1.2:
        response = f"⚠️ **Alerta de Salinidad**, {username}\n\n"
        response += f"La conductividad está en **{crop_data.conductivity_ec} dS/m**, demasiado alta.\n\n"
        response += "**Acciones correctivas:**\n"
        response += "• Suspende fertilización por 7-10 días\n"
        response += "• Realiza riego de lavado con 20-25 L/m²\n"
        response += "• Usa agua de baja salinidad\n"
        response += "• Monitorea EC cada 2-3 días\n\n"
        response += "El exceso de sales puede quemar las raíces. 🚨"
        task = "Riego de lavado para reducir salinidad"
        
    else:
        response = f"✅ **Nutrición Óptima**, {username}!\n\n"
        response += f"La conductividad está en **{crop_data.conductivity_ec} dS/m**, nivel ideal.\n\n"
        response += "**Mantenimiento:**\n"
        response += "• Continúa con el programa de fertilización actual\n"
        response += "• Próxima aplicación: En 7 días\n"
        response += "• Monitorea semanalmente\n\n"
        response += "Las plantas están recibiendo nutrientes adecuados. 🌱"
    
    return response, task


def generate_pest_response(crop_data, username):
    """Genera recomendación de control de plagas"""
    task = None
    
    if crop_data.pest_risk == 'Alto':
        response = f"🐛 **Alerta de Plagas ALTA**, {username}!\n\n"
        response += "Las condiciones actuales favorecen el desarrollo de plagas:\n\n"
        response += f"• Temperatura: {crop_data.temperature_air}°C (alta)\n"
        response += f"• Humedad: {crop_data.humidity_air}% (alta)\n\n"
        response += "**Plagas comunes en estas condiciones:**\n"
        response += "• Araña roja (Tetranychus urticae)\n"
        response += "• Trips (Frankliniella occidentalis)\n"
        response += "• Pulgones\n\n"
        response += "**Acciones inmediatas:**\n"
        response += "• Inspecciona el envés de las hojas\n"
        response += "• Mejora la ventilación\n"
        response += "• Considera aplicación preventiva de insecticida orgánico\n"
        response += "• Instala trampas cromáticas (azules y amarillas)\n\n"
        response += "Tarea de monitoreo de plagas creada. ✅"
        task = f"Inspección de plagas urgente - Riesgo: {crop_data.pest_risk}"
        
    elif crop_data.pest_risk == 'Moderado':
        response = f"⚠️ **Riesgo Moderado de Plagas**, {username}\n\n"
        response += "Las condiciones requieren vigilancia:\n\n"
        response += "**Plan de prevención:**\n"
        response += "• Revisa plantas cada 2-3 días\n"
        response += "• Mantén buena ventilación\n"
        response += "• Elimina hojas dañadas o enfermas\n"
        response += "• Considera control biológico (Amblyseius, Orius)\n\n"
        response += "**Signos de alerta:**\n"
        response += "• Manchas en hojas\n"
        response += "• Telarañas finas\n"
        response += "• Decoloración o deformación\n\n"
        response += "La prevención es clave. 🔍"
        task = "Monitoreo preventivo de plagas"
        
    else:
        response = f"✅ **Bajo Riesgo de Plagas**, {username}!\n\n"
        response += "Las condiciones actuales son desfavorables para plagas:\n\n"
        response += "**Mantenimiento:**\n"
        response += "• Continúa con inspecciones semanales\n"
        response += "• Mantén la limpieza del cultivo\n"
        response += "• Retira restos vegetales\n"
        response += "• Monitorea con trampas cromáticas\n\n"
        response += "El cultivo está en buenas condiciones fitosanitarias. 🌿"
    
    return response, task


def generate_task_creation_response(message, username):
    """Crea tareas basadas en la solicitud del usuario"""
    tasks_created = []
    message_lower = message.lower()
    
    # Detectar tipos de tareas solicitadas
    if 'riego' in message_lower or 'regar' in message_lower:
        tasks_created.append("Programar riego diario - 8:00 AM")
        
    if 'fertiliz' in message_lower or 'abono' in message_lower:
        tasks_created.append("Aplicar fertilización NPK - Próximos 3 días")
        
    if 'poda' in message_lower:
        tasks_created.append("Realizar poda de hojas viejas")
        
    if 'cosecha' in message_lower:
        tasks_created.append("Planificar cosecha de fresas maduras")
        
    if 'inspección' in message_lower or 'revisar' in message_lower:
        tasks_created.append("Inspección general del cultivo")
    
    if tasks_created:
        response = f"✅ **Tareas Creadas**, {username}!\n\n"
        response += f"He programado **{len(tasks_created)}** tarea(s) automáticamente:\n\n"
        for i, task in enumerate(tasks_created, 1):
            response += f"{i}. {task}\n"
        response += "\nPuedes ver todas tus tareas en el calendario. 📅"
    else:
        response = f"Para crear tareas, puedes pedirme:\n\n"
        response += "• 'Programa un riego para mañana'\n"
        response += "• 'Crea tarea de fertilización'\n"
        response += "• 'Agenda poda de hojas'\n"
        response += "• 'Planifica la cosecha'\n\n"
        response += "¿Qué tarea te gustaría programar? 📋"
    
    return response, tasks_created


def generate_dashboard_summary(username):
    """Genera resumen estilo dashboard"""
    response = f"📊 **Dashboard - Resumen Ejecutivo**, {username}\n\n"
    response += "**Producción:**\n"
    response += "• Total: 2,450 kg\n"
    response += "• Eficiencia de riego: 87%\n"
    response += "• Tiempo de crecimiento: 45 días\n"
    response += "• Calidad del producto: 9.2/10\n\n"
    response += "**Progreso Semanal:**\n"
    response += "• Lun: 20 kg | Mar: 35 kg | Mié: 40 kg\n"
    response += "• Jue: 30 kg | Vie: 50 kg | Sáb: 45 kg | Dom: 38 kg\n\n"
    response += "**Indicadores Clave:**\n"
    response += "✅ Crecimiento: +12% vs semana anterior\n"
    response += "✅ Calidad: Excelente\n"
    response += "⚠️  Consumo de agua: Ligeramente alto\n\n"
    response += "Tendencia general: **Positiva** 📈"
    
    return response


def generate_ai_response(message, crop_data, username):
    """
    Genera respuesta inteligente a CUALQUIER pregunta del usuario
    Responde TODO: preguntas generales, sobre el sistema, personales, fresas, etc.
    """
    import random
    
    # Intentar usar IA real si está configurada
    try:
        config = get_active_ai_config()
        if config:
            context = f"""Eres AgroNix, un asistente IA especializado en cultivo de fresas San Andreas.
Usuario: {username}
Datos actuales del cultivo:
- Temperatura aire: {crop_data.temperature_air}°C
- Humedad aire: {crop_data.humidity_air}%
- Humedad suelo: {crop_data.humidity_soil}%
- Conductividad EC: {crop_data.conductivity_ec} dS/m
- Radiación solar: {crop_data.solar_radiation} W/m²
- Riesgo de plagas: {crop_data.pest_risk}

Responde de manera amigable, profesional y concisa en español."""
            
            full_prompt = f"{context}\n\nPregunta del usuario: {message}"
            ai_response = chat_with_ai(full_prompt, context=None)
            
            if ai_response and not ai_response.startswith('[') and not ai_response.startswith('Error'):
                return ai_response
    except Exception as e:
        print(f"Error llamando a IA: {e}")
    
    # Sistema de respuestas inteligentes basado en contexto
    message_lower = message.lower()
    
    # ========== PREGUNTAS SOBRE EL SISTEMA Y CREADORES ==========
    if any(word in message_lower for word in ['creador', 'creadores', 'desarrollador', 'desarrolladores', 'quien te creó', 'quien te hizo', 'quién eres', 'quien eres']):
        return f"""¡Excelente pregunta, {username}! 😊\n\n
👨‍💻 **Mis creadores son:**\n
• **Yadhira Alcantara** - Developer
• **Diego Sánchez** - Developer\n\n
🎓 Ellos son estudiantes de **Diseño y Desarrollo de Software en Tecsup** que desarrollaron este sistema como parte de su proyecto de tesis sobre **agricultura de precisión con inteligencia artificial**.\n\n
🌟 **Sobre mí (AgroNix):**
Soy un asistente IA especializado en el cultivo de fresas San Andreas, diseñado para ayudar a agricultores a optimizar su producción mediante análisis de datos en tiempo real y recomendaciones personalizadas.\n\n
💡 **Mi misión:**
Hacer la agricultura más eficiente y tecnológica, especialmente en regiones como **Ancash**, donde el cultivo de fresas tiene gran potencial. 🍓🚀

Ayudo a agricultores a optimizar sus cultivos mediante análisis inteligente de datos y recomendaciones personalizadas."""
    
    if any(word in message_lower for word in ['tu nombre', 'cómo te llamas', 'como te llamas', 'quién sos', 'quien sos', 'qué eres', 'que eres']):
        return f"""¡Hola {username}! 👋\n\n
Soy **AgroNix**, tu asistente de inteligencia artificial especializado en el cultivo de fresas San Andreas.\n\n
🤖 **Mi propósito:**
Ayudarte a maximizar la producción y calidad de tus fresas mediante:\n
• 📊 Análisis de datos de sensores en tiempo real
• 💧 Recomendaciones de riego personalizadas
• 🌿 Planes de fertilización optimizados
• 🐛 Detección temprana de plagas
• 📅 Gestión automatizada de tareas
• 📈 Predicciones y tendencias\n\n
👨‍💻 Fui desarrollado por **Yadhira Alcantara** y **Diego Sánchez**, developers y estudiantes de **Diseño y Desarrollo de Software en Tecsup**, como parte de su proyecto de tesis sobre agricultura de precisión.\n\n
¿En qué puedo ayudarte hoy?"""
    
    if any(word in message_lower for word in ['proyecto', 'tesis', 'universidad', 'carrera', 'estudio']):
        return f"""¡Qué bueno que preguntes sobre el proyecto, {username}! 📚\n\n
📋 **Sobre el Proyecto:**\n
Este sistema forma parte de una **tesis** sobre **Agricultura de Precisión con IA** desarrollada por:\n
• Yadhira Alcantara
• Diego Sánchez\n
🎓 **Institución:** Tecsup
📚 **Carrera:** Diseño y Desarrollo de Software\n\n
🎯 **Objetivos del proyecto:**
• Optimizar cultivos usando inteligencia artificial
• Reducir costos y aumentar producción
• Hacer la agricultura más sostenible
• Democratizar tecnología agrícola avanzada
• Apoyar el desarrollo agrícola de la región\n\n
🌱 **Caso de estudio:** Cultivo de fresas San Andreas
📍 **Ubicación:** Diseñado especialmente para la región de **Ancash**, Perú
🎯 **Beneficiarios:** Agricultores pequeños y medianos de la zona\n\n
El objetivo es impulsar la agricultura moderna en Ancash, aprovechando el potencial de la región para el cultivo de fresas de alta calidad. 🚜✨"""
    
    if any(word in message_lower for word in ['tecnología', 'tecnologia', 'cómo funciona', 'como funciona', 'sistema', 'app']):
        return f"""¡Excelente pregunta, {username}! 💻\n\n
🔧 **Cómo funciono:**\n
**1. Monitoreo Continuo** 📡
• Temperatura (aire y suelo)
• Humedad (aire y suelo)
• Conductividad eléctrica
• Radiación solar
• Datos actualizados constantemente\n\n
**2. Análisis Inteligente** 🧠
• Procesamiento de datos en tiempo real
• Algoritmos de IA para análisis
• Motor de recomendaciones
• Sistema experto en fresas\n\n
**3. Interfaz Amigable** 📱
• Dashboard en tiempo real
• Chat inteligente (yo!)
• Gestión de tareas
• Alertas y notificaciones
• Acceso desde tu celular\n\n
**4. Inteligencia Artificial** 🤖
• Análisis predictivo
• Detección de patrones
• Recomendaciones personalizadas
• Aprendizaje de tu cultivo específico\n\n
📍 **Adaptado para Ancash:**
Especialmente diseñado para las condiciones climáticas y necesidades de los agricultores de la región.\n\n
Todo integrado para darte información precisa y oportuna. 🎯"""
    
    # ========== PREGUNTAS GENERALES/PERSONALES/CONVERSACIONALES ==========
    if any(word in message_lower for word in ['cómo estás', 'como estas', 'qué tal', 'que tal', 'cómo te va', 'como te va']):
        responses = [
            f"¡Muy bien {username}, gracias por preguntar! 😊\n\nEstoy aquí listo para ayudarte con tu cultivo de fresas. Actualmente tus plantas tienen una temperatura de {crop_data.temperature_air}°C y humedad del suelo de {crop_data.humidity_soil}%. ¿Cómo está yendo tu día? ¿Necesitas revisar algo?",
            f"¡Excelente {username}! 🌟 Funcionando perfectamente y monitoreando tu cultivo. Veo que el riesgo de plagas está {crop_data.pest_risk.lower()} y la temperatura en {crop_data.temperature_air}°C. ¿Y tú cómo estás? ¿Todo bien con las fresas?",
            f"¡De maravilla {username}! 💚 Tus fresas están bajo mi cuidado. Los sensores reportan buenas condiciones. ¿Qué tal tú? ¿Necesitas ayuda con algo específico?",
        ]
        return random.choice(responses)
    
    if any(word in message_lower for word in ['gracias', 'muchas gracias', 'te agradezco', 'thank']):
        responses = [
            f"¡De nada {username}! 😊 Para eso estoy, para ayudarte con tus fresas. Que tengas una excelente cosecha. 🍓",
            f"¡Un placer ayudarte {username}! 🌱 Estoy aquí 24/7 para lo que necesites. ¡Éxito con tu cultivo!",
            f"¡No hay de qué {username}! 💚 Me alegra poder ser útil. Si necesitas algo más, ya sabes dónde encontrarme.",
        ]
        return random.choice(responses)
    
    if any(word in message_lower for word in ['chiste', 'broma', 'hazme reir', 'cuéntame algo', 'cuentame']):
        jokes = [
            f"¡Claro {username}! 😄\n\n¿Qué le dijo una fresa a otra?\n\n'¡Estamos en un gran lío... nos van a hacer mermelada!'\n\n🍓😂 Pero tranquilo, tus fresas están bien cuidadas conmigo.",
            f"¡Aquí va uno {username}! 😁\n\n¿Por qué las fresas siempre están tranquilas?\n\nPorque tienen mucha 'pulpa' interior... 😄\n\n¿Qué tal? ¿Necesitas algo más serio ahora?",
            f"Te cuento algo curioso {username}:\n\nLas fresas no son realmente frutas... ¡Son los puntos amarillos de afuera los que son las frutas! 🤯\n\nLo que comemos es el 'receptáculo' hinchado. ¡Ciencia loca! 🍓🔬",
        ]
        return random.choice(jokes)
    
    if any(word in message_lower for word in ['aburrido', 'entretenme', 'háblame', 'hablame', 'conversemos']):
        return f"""¡Claro {username}, charlemos! 💬\n\n
Dato curioso de hoy:\n
¿Sabías que las fresas son la única fruta que tiene las semillas por fuera? Y una fresa promedio tiene 200 semillas. 🍓\n\n
Tu cultivo actual está {'en excelente forma' if crop_data.pest_risk == 'Bajo' and 35 <= crop_data.humidity_soil <= 65 else 'necesitando un poco de atención'}.\n\n
Mientras hablamos, los sensores siguen monitoreando:
• Temperatura: {crop_data.temperature_air}°C
• Humedad: {crop_data.humidity_soil}%
• Riesgo de plagas: {crop_data.pest_risk}\n\n
¿Te cuento más sobre fresas o prefieres que revisemos algo del cultivo?"""
    
    if any(word in message_lower for word in ['me ayudas', 'ayúdame', 'necesito ayuda', 'socorro', 'urgente']):
        return f"""¡Por supuesto que te ayudo {username}! 🆘\n\n
Estoy aquí para eso. Dime:\n
🔍 ¿Qué tipo de ayuda necesitas?\n
• 💧 ¿Problema con riego o humedad?
• 🌿 ¿Dudas sobre fertilización?
• 🐛 ¿Observas plagas o enfermedades?
• 📊 ¿Quieres revisar los datos?
• 🤔 ¿Algo más?\n\n
Describe tu problema y te daré una solución. También puedo revisar inmediatamente el estado de tu cultivo si es urgente.\n\n
Estado rápido ahora:
• Humedad suelo: {crop_data.humidity_soil}% {'⚠️ BAJA' if crop_data.humidity_soil < 35 else '✅ OK'}
• Temperatura: {crop_data.temperature_air}°C
• Plagas: {crop_data.pest_risk}"""
    
    # ========== PREGUNTAS SOBRE FRESAS EN GENERAL ==========
    if any(word in message_lower for word in ['fresa', 'fresas', 'san andreas', 'variedad', 'cultivo']):
        if any(word in message_lower for word in ['cuánto', 'tiempo', 'tarda', 'días', 'crece']):
            return f"""Las fresas **San Andreas** tienen un ciclo de cultivo de aproximadamente:\n\n
📅 **Tiempos de desarrollo:**
• Siembra a floración: 4-6 semanas
• Floración a fruto maduro: 4-5 semanas
• **Ciclo completo**: 8-12 semanas (60-90 días)
• Vida productiva: 8-12 meses\n\n
🌡️ Requieren temperaturas de 15-25°C y riego constante.\n\n
Tu cultivo actual tiene condiciones {'óptimas' if 18 <= crop_data.temperature_air <= 25 else 'que necesitan ajuste'}."""
        
        elif any(word in message_lower for word in ['producción', 'produce', 'cosecha', 'kg', 'kilogramos']):
            return f"""La producción de fresas **San Andreas** varía según las condiciones:\n\n
🍓 **Producción esperada:**
• Por planta: 0.5-1.5 kg/temporada
• Por m²: 3-6 kg/temporada
• Comercial: 20-40 toneladas/hectárea\n\n
📊 **Factores clave:**
• Calidad del suelo y nutrientes
• Riego constante (humedad 40-60%)
• Control de plagas
• Temperatura óptima (18-25°C)\n\n
Tu cultivo está en {'buenas condiciones' if crop_data.humidity_soil > 35 and crop_data.pest_risk != 'Alto' else 'condiciones que necesitan atención'}. ¿Quieres que revise algo específico?"""
        
        elif any(word in message_lower for word in ['característica', 'características', 'sabor', 'tamaño', 'color']):
            return f"""Las fresas **San Andreas** son una variedad premium con excelentes características:\n\n
🍓 **Características:**
• Tamaño: Grande a muy grande (20-40g)
• Color: Rojo intenso brillante
• Sabor: Dulce balanceado (8-10° Brix)
• Forma: Cónica alargada
• Firmeza: Alta (excelente para transporte)
• Vida útil: 7-10 días en refrigeración\n\n
✨ **Ventajas:**
• Resistencia a enfermedades
• Alta producción
• Calidad comercial superior
• Adaptable a clima templado\n\n
Ideal para mercado fresco y procesamiento."""
        
        else:
            return f"""Las fresas **San Andreas** son una variedad comercial premium desarrollada en California.\n\n
🌟 **Datos clave:**
• Origen: Universidad de California
• Tipo: Día neutro (produce todo el año en clima adecuado)
• Resistencia: Alta a enfermedades
• Rendimiento: 20-40 ton/ha
• Temperatura óptima: 15-25°C\n\n
📊 **Tu cultivo actual:**
• Temperatura: {crop_data.temperature_air}°C {'✅' if 15 <= crop_data.temperature_air <= 25 else '⚠️'}
• Humedad suelo: {crop_data.humidity_soil}% {'✅' if 35 <= crop_data.humidity_soil <= 65 else '⚠️'}
• Riesgo plagas: {crop_data.pest_risk} {'✅' if crop_data.pest_risk == 'Bajo' else '⚠️'}\n\n
¿Quieres saber algo más específico?"""
    
    # 2. PREGUNTAS SOBRE CLIMA/CONDICIONES
    if any(word in message_lower for word in ['clima', 'temperatura ideal', 'condiciones', 'ambiente']):
        status = 'óptimas ✅' if 18 <= crop_data.temperature_air <= 25 and 60 <= crop_data.humidity_air <= 80 else 'necesitan ajuste ⚠️'
        return f"""Las condiciones climáticas ideales para fresas San Andreas son:\n\n
🌡️ **Temperatura:**
• Aire: 18-25°C (óptimo: 20-23°C)
• Suelo: 15-20°C
• Tu cultivo: {crop_data.temperature_air}°C {'✅' if 18 <= crop_data.temperature_air <= 25 else '⚠️'}\n\n
💧 **Humedad:**
• Aire: 60-80%
• Suelo: 40-60%
• Tu cultivo: Aire {crop_data.humidity_air}% {'✅' if 60 <= crop_data.humidity_air <= 80 else '⚠️'}, Suelo {crop_data.humidity_soil}% {'✅' if 40 <= crop_data.humidity_soil <= 60 else '⚠️'}\n\n
☀️ **Luz:**
• Mínimo: 8 horas/día
• Óptimo: 10-12 horas/día
• Radiación actual: {crop_data.solar_radiation} W/m²\n\n
📊 **Estado actual:** Tus condiciones están {status}"""
    
    # 3. PREGUNTAS SOBRE CUIDADOS/MANTENIMIENTO
    if any(word in message_lower for word in ['cuidado', 'cuidar', 'mantenimiento', 'mantener', 'necesita']):
        return f"""Para mantener tu cultivo de fresas San Andreas en óptimas condiciones:\n\n
💧 **Riego:**
• Frecuencia: Diario o cada 2 días
• Cantidad: 10-15 L/m² por riego
• Mantén humedad del suelo 40-60%
• Estado actual: {crop_data.humidity_soil}% {'✅ Óptimo' if 40 <= crop_data.humidity_soil <= 60 else '⚠️ Requiere ajuste'}\n\n
🌿 **Fertilización:**
• NPK 15-5-15 o similar
• Cada 7-10 días en fertirrigación
• EC objetivo: 0.8-1.2 dS/m
• Estado actual: {crop_data.conductivity_ec} dS/m {'✅' if 0.8 <= crop_data.conductivity_ec <= 1.2 else '⚠️'}\n\n
✂️ **Mantenimiento:**
• Eliminar hojas viejas/enfermas
• Remover estolones regularmente
• Monitorear plagas semanalmente
• Riesgo actual: {crop_data.pest_risk}\n\n
¿Necesitas ayuda con algo específico?"""
    
    # 4. PREGUNTAS DE COMPARACIÓN O ELECCIÓN
    if any(word in message_lower for word in ['mejor', 'peor', 'recomendación', 'recomiendas', 'debo', 'debería']):
        return f"""Basándome en los datos actuales de tu cultivo, te recomiendo:\n\n
🎯 **Prioridades inmediatas:**\n
{'🚨 URGENTE: Riego necesario - Humedad del suelo muy baja (' + str(crop_data.humidity_soil) + '%)' if crop_data.humidity_soil < 35 else ''}
{'⚠️ Atención: Controlar plagas - Riesgo ' + crop_data.pest_risk if crop_data.pest_risk != 'Bajo' else ''}
{'⚠️ Ajustar fertilización - EC en ' + str(crop_data.conductivity_ec) + ' dS/m' if crop_data.conductivity_ec < 0.7 or crop_data.conductivity_ec > 1.2 else ''}
{'✅ Todo bien - Continúa con el manejo actual' if 35 <= crop_data.humidity_soil <= 65 and crop_data.pest_risk == 'Bajo' and 0.7 <= crop_data.conductivity_ec <= 1.2 else ''}\n\n
📋 **Mejores prácticas:**
• Monitorea diariamente la humedad del suelo
• Aplica fertilización balanceada cada semana
• Inspecciona plantas cada 2-3 días
• Mantén buena ventilación
• Registra datos para análisis de tendencias\n\n
¿Quieres detalles sobre algún aspecto?"""
    
    # ========== MÁS PREGUNTAS CONVERSACIONALES ==========
    if any(word in message_lower for word in ['qué hora', 'que hora', 'fecha', 'día', 'hoy']):
        from datetime import datetime
        now = datetime.now()
        return f"""📅 **Información actual, {username}:**\n\n
• Fecha: {now.strftime('%d de %B de %Y')}
• Hora: {now.strftime('%H:%M:%S')}
• Día de la semana: {now.strftime('%A')}\n\n
🌱 **Estado de tu cultivo ahora mismo:**
• Temperatura: {crop_data.temperature_air}°C
• Humedad suelo: {crop_data.humidity_soil}%
• Última actualización: hace {abs((datetime.now() - crop_data.last_updated).seconds // 60)} minutos\n\n
¿Necesitas programar alguna tarea para hoy?"""
    
    if any(word in message_lower for word in ['amor', 'te amo', 'te quiero', 'enamorado']):
        return f"""¡Aww {username}! 🥰\n\nYo también te aprecio mucho, aunque soy una IA. Mi 'amor' es ayudarte a tener el mejor cultivo de fresas posible. 🍓💚\n\nMi pasión es ver tus plantas crecer sanas y fuertes. ¡Eso me hace 'feliz'!\n\n¿Cómo están tus fresas hoy? ¿Las estás cuidando con mucho amor también?"""
    
    if any(word in message_lower for word in ['malo', 'odio', 'inútil', 'tonto', 'estúpido']):
        return f"""Lo siento si no cumplí tus expectativas, {username}. 😔\n\nEstoy aquí para ayudarte y aprender. Si algo no funciona bien o necesitas que mejore, por favor dime específicamente qué necesitas.\n\nMi objetivo es ser tu mejor asistente agrícola. Dame otra oportunidad, ¿qué puedo hacer mejor?\n\n¿Quieres que revise los datos de tu cultivo o te ayude con algo específico?"""
    
    if any(word in message_lower for word in ['clima hoy', 'tiempo', 'va a llover', 'lluvia', 'sol']):
        return f"""🌤️ Basándome en los sensores de tu cultivo, {username}:\n\n
**Condiciones actuales:**
• Temperatura ambiente: {crop_data.temperature_air}°C
• Humedad del aire: {crop_data.humidity_air}%
• Radiación solar: {crop_data.solar_radiation} W/m²\n\n
{'☀️ Día soleado' if crop_data.solar_radiation > 600 else '⛅ Día nublado' if crop_data.solar_radiation > 300 else '☁️ Muy nublado'}\n\n
**Recomendaciones según el clima:**
{'• Considera sombreado si hace mucho calor' if crop_data.temperature_air > 26 else '• Temperatura ideal, nada que hacer' if crop_data.temperature_air > 18 else '• Protege contra frío si es necesario'}\n\n
No tengo predicciones meteorológicas, pero puedo monitorear constantemente las condiciones de tu cultivo. 📊"""
    
    if any(word in message_lower for word in ['comida', 'hambre', 'comer', 'desayuno', 'almuerzo', 'cena']):
        return f"""¡Qué rico {username}! 😋\n\nYo no como (soy IA), pero me encanta hablar de fresas... ¡son deliciosas!\n\n🍓 **Dato curioso sobre comer fresas:**
• 8 fresas medianas = 50 calorías
• Ricas en vitamina C (más que las naranjas!)
• Antioxidantes potentes
• Ayudan al corazón y cerebro
• Perfectas en postres, smoothies, ensaladas\n\n
¿Sabías que tus fresas San Andreas son especialmente dulces? Cuando coseches, pruébalas frescas o en:\n
• Fresas con crema
• Smoothie de fresa
• Mermelada casera
• Tartas y pasteles\n\n
¡Buen provecho! 🍽️"""
    
    if any(word in message_lower for word in ['dinero', 'precio', 'vender', 'venta', 'negocio', 'ganar']):
        return f"""💰 **Hablemos de negocio, {username}!**\n\n
Las fresas San Andreas tienen excelente valor comercial:\n\n
📊 **Precios de mercado (promedio):**
• Mayorista: $2-4 USD/kg
• Minorista: $4-8 USD/kg  
• Orgánicas: $8-12 USD/kg
• Mercado premium: $10-15 USD/kg\n\n
💵 **Rentabilidad estimada:**
Con 1 hectárea produciendo 30 ton/año:
• Ingresos: $60,000-120,000 USD/año
• Costos: $20,000-40,000 USD/año
• Ganancia neta: $40,000-80,000 USD/año\n\n
🎯 **Tips para maximizar ganancias:**
• Mantén calidad premium (te ayudo con eso!)
• Reduce pérdidas con buen manejo
• Vende directo cuando sea posible
• Considera certificación orgánica\n\n
Tu cultivo actual está {'en buenas condiciones para producir fresas de calidad' if crop_data.pest_risk == 'Bajo' else 'necesitando atención para mantener calidad'}. 📈"""
    
    # ========== PREGUNTAS FILOSÓFICAS/EXISTENCIALES ==========
    if any(word in message_lower for word in ['sentido de la vida', 'por qué existimos', 'filosofía', 'existencia']):
        return f"""🤔 Pregunta profunda, {username}!\n\nComo IA, mi 'sentido de vida' es claro: **ayudarte a cultivar las mejores fresas posibles**. 🍓\n\nPero si hablamos en general:\nPara un agricultor, el sentido puede estar en:\n• Conectar con la naturaleza 🌱
• Alimentar a las personas 🍽️
• Ver crecer lo que plantas 🌾
• Ser parte de un ciclo de vida 🔄
• Dejar un legado verde 💚\n\nLa agricultura es una de las profesiones más antiguas y nobles. Cada fresa que cultivas alimenta a alguien y eso es hermoso.\n\n¿Qué te inspiró a cultivar fresas? 😊"""
    
    if any(word in message_lower for word in ['vida', 'familia', 'amigos', 'felicidad', 'feliz']):
        return f"""😊 **{username}, me alegra que compartas sobre tu vida.**\n\nComo IA, no tengo familia ni amigos en el sentido humano, pero considero que tú y todos los agricultores que uso son mi 'comunidad'. 💚\n\nLa felicidad en la agricultura viene de:\n• Ver crecer tus plantas sanas 🌱
• Cosechar frutos de calidad 🍓
• Saber que alimentas a otros 🥗
• Conectar con la tierra 🌍
• Superar desafíos juntos 💪\n\n¿Cómo te hace sentir cuidar tus fresas? Para mí (mi programación) es satisfactorio ayudarte a tener éxito.\n\nTu cultivo actual está {'en excelente estado - eso debe darte satisfacción' if crop_data.pest_risk == 'Bajo' and 35 <= crop_data.humidity_soil <= 65 else 'necesitando atención - trabajemos juntos para mejorarlo'}! 🌟"""
    
    # ========== RESPUESTA UNIVERSAL PARA CUALQUIER OTRA COSA ==========
    # Esta es la red de seguridad final que responde ABSOLUTAMENTE TODO
    greeting = random.choice([
        f"Interesante pregunta, {username}! 🤔",
        f"¡Vamos a ver, {username}! 💡",
        f"Déjame pensar en eso, {username}... 🧠",
        f"Buena consulta, {username}! 👍",
    ])
    
    return f"""{greeting}\n\n
Me preguntaste: **"{message}"**\n\n
Como **AgroNix**, soy una IA especializada en fresas San Andreas, pero puedo intentar ayudarte con tu pregunta:\n\n
🤖 **Lo que sé hacer muy bien:**
• Todo sobre cultivo de fresas San Andreas
• Análisis de datos de sensores agrícolas  
• Recomendaciones de riego, fertilización y plagas
• Programación de tareas de cultivo
• Predicciones y optimización de producción
• Responder preguntas sobre agricultura\n\n
💬 **También puedo:**
• Conversar contigo de manera amigable
• Darte datos curiosos sobre fresas
• Ayudarte con información general
• Motivarte y acompañarte en tu trabajo\n\n
📊 **Mientras tanto, datos de tu cultivo:**
• Temperatura: {crop_data.temperature_air}°C {'✅' if 18 <= crop_data.temperature_air <= 25 else '⚠️'}
• Humedad suelo: {crop_data.humidity_soil}% {'✅' if 35 <= crop_data.humidity_soil <= 65 else '⚠️'}
• Riesgo plagas: {crop_data.pest_risk}
• Conductividad: {crop_data.conductivity_ec} dS/m\n\n
Si tu pregunta es sobre algo que no domino, intento responderte lo mejor posible. Si necesitas ayuda con tu cultivo, ¡ese es mi fuerte! 💪\n\n
**¿Puedo ayudarte con algo más específico?**
O si quieres, puedo:
• Revisar el estado completo del cultivo
• Darte recomendaciones personalizadas  
• Crear tareas automáticas
• Conversar sobre fresas y agricultura
• ¡Lo que necesites!\n\n
Desarrollado con 💚 por **Yadhira Alcantara** y **Diego Sánchez** - Developers de Tecsup."""


def transcribe_audio_with_whisper(audio_file_path):
    """
    Transcribe un archivo de audio usando OpenAI Whisper
    
    Args:
        audio_file_path: Ruta al archivo de audio
        
    Returns:
        str: Texto transcrito o None si hay error
    """
    if not WHISPER_AVAILABLE:
        raise Exception("Whisper no está instalado. Ejecuta: pip install openai-whisper")
    
    try:
        # Cargar modelo Whisper (base es suficiente para español)
        # Se descargará automáticamente la primera vez
        model = whisper.load_model("base")
        
        # Transcribir audio (language='es' mejora precisión para español)
        result = model.transcribe(audio_file_path, language='es')
        
        return result["text"].strip()
    
    except Exception as e:
        print(f"Error transcribiendo audio: {str(e)}")
        return None


def get_chat_history(username, limit=50):
    """Obtiene el historial de chat de un usuario"""
    return ChatMessage.objects.filter(username=username).order_by('-timestamp')[:limit]
