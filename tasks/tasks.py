from celery import shared_task
from alerts.models import AlertRule, Alert
from sensors.mongo import last_reading

ops = {
    '>':  lambda v,t: v > t,
    '<':  lambda v,t: v < t,
    '>=': lambda v,t: v >= t,
    '<=': lambda v,t: v <= t,
    '==': lambda v,t: v == t,
}

@shared_task
def evaluate_alert_rules():
    for rule in AlertRule.objects.filter(activo=True).select_related('sensor'):
        doc = last_reading(rule.sensor.ext_collection, rule.sensor.ext_sensor_id)
        if not doc: 
            continue
        val = float(doc.get('value'))
        if ops[rule.operador](val, rule.umbral):
            Alert.objects.create(
                sensor=rule.sensor,
                valor=val,
                mensaje=f'{rule.sensor.nombre}: {val} {rule.sensor.unidad} {rule.operador} {rule.umbral}',
                rule=rule,
            )