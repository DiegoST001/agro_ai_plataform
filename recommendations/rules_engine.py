from django.utils import timezone
from datetime import timedelta
from recommendations.models import Recommendation
from tasks.models import Task
from parcels.models import Parcela, Ciclo
from crops.models import ReglaPorEtapa
from agro_ai_platform.mongo import get_db

def upsert_alert(parcela, titulo, detalle, code, severity='info',
                 entity_type='', entity_ref='', meta=None, expires_at=None, source='rules'):
    fp = f"{code}:{parcela.id}:{entity_type}:{entity_ref}"
    defaults = {
        'parcela': parcela,
        'titulo': titulo,
        'detalle': detalle,
        'severity': severity,
        'status': 'new',
        'tipo': 'alerta',
        'score': 1.0,
        'source': source,
        'code': code,
        'entity_type': entity_type or '',
        'entity_ref': entity_ref or '',
        'meta': meta or {},
        'expires_at': expires_at,
    }
    obj, created = Recommendation.objects.get_or_create(fingerprint=fp, defaults=defaults)
    if not created:
        changed = False
        for k,v in defaults.items():
            if k in ('status',):  # no sobrescribir status
                continue
            if getattr(obj,k) != v:
                setattr(obj,k,v)
                changed = True
        if changed:
            obj.save()
    return obj

def rule_tasks_due(days=3):
    now = timezone.now()
    end = now + timedelta(days=days)
    qs = Task.all_objects.filter(
        fecha_programada__gte=now,
        fecha_programada__lte=end,
        estado__in=['pendiente','en_progreso'],
        deleted_at__isnull=True
    ).select_related('parcela')
    for t in qs:
        dleft = max(0, (t.fecha_programada - now).days)
        code = f"task_due_{dleft}d"
        titulo = "Tarea para hoy" if dleft == 0 else f"Tarea en {dleft} día(s)"
        detalle = f"{t.tipo} - {t.descripcion[:80]}..."
        sev = 'high' if dleft == 0 else ('medium' if dleft == 1 else 'low')
        meta = {
            'task_id': t.id,
            'fecha_programada': t.fecha_programada.isoformat(),
            'estado': t.estado,
            'days_left': dleft
        }
        upsert_alert(t.parcela, titulo, detalle, code, severity=sev,
                     entity_type='task', entity_ref=str(t.id), meta=meta, source='rules.task_due')

def rule_parcela_created(parcela):
    upsert_alert(parcela, "Nueva parcela registrada",
                 f"Parcela '{parcela.nombre}' creada.", "parcela_creada",
                 severity='info', entity_type='parcela', entity_ref=str(parcela.id))

def rule_parcela_without_active_ciclo(parcela):
    if not parcela.ciclos.filter(estado='activo').exists():
        upsert_alert(parcela, "Parcela sin ciclo activo",
                     "No hay ciclo activo asociado.", "parcela_sin_ciclo",
                     severity='medium', entity_type='parcela', entity_ref=str(parcela.id))

def rule_ciclo_closed(ciclo):
    upsert_alert(ciclo.parcela, "Ciclo cerrado",
                 f"Ciclo {ciclo.id} cerrado el {ciclo.fecha_cierre}.",
                 f"ciclo_cerrado_{ciclo.id}", severity='info',
                 entity_type='ciclo', entity_ref=str(ciclo.id))

def rule_stage_advanced(ciclo):
    if ciclo.etapa_actual:
        upsert_alert(ciclo.parcela, "Etapa avanzada",
                     f"Avanzó a etapa '{ciclo.etapa_actual.nombre}'.",
                     f"etapa_avanzada_{ciclo.id}_{ciclo.etapa_actual.id}",
                     severity='info', entity_type='ciclo', entity_ref=str(ciclo.id),
                     meta={'etapa_id': ciclo.etapa_actual.id})

def rule_stage_param_breach():
    db = get_db()
    now = timezone.now()
    # simplificación: tomar lecturas últimas 6h
    since = now - timedelta(hours=6)
    # reglas activas
    reglas = ReglaPorEtapa.objects.filter(activo=True)
    # (Implementar agregados según estructura real de lecturas)
    # Pseudocódigo para cada regla: evaluar promedio y disparar alerta
    for reg in reglas:
        etapa = reg.etapa
        ciclos = etapa.ciclos_en_etapa.filter(estado='activo').select_related('parcela')
        for ciclo in ciclos:
            # valor ficticio (debe agregarse desde Mongo)
            valor = None
            if valor is None:
                continue
            breach = False
            if reg.minimo is not None and valor < reg.minimo:
                breach = 'menor'
            if reg.maximo is not None and valor > reg.maximo:
                breach = 'mayor'
            if breach:
                code = f"regla_breach_{reg.id}_{ciclo.id}"
                titulo = f"Parámetro fuera de rango ({reg.parametro})"
                detalle = f"Valor={valor} ({'<' if breach=='menor' else '>'} límite)."
                sev = 'high' if breach=='mayor' else 'medium'
                meta = {'regla_id': reg.id, 'ciclo_id': ciclo.id, 'parametro': reg.parametro, 'valor': valor}
                upsert_alert(ciclo.parcela, titulo, detalle, code, severity=sev,
                             entity_type='regla', entity_ref=str(reg.id), meta=meta, source='rules.reglas')