from django.db.models.signals import post_save
from django.dispatch import receiver
from parcels.models import Parcela, Ciclo
from recommendations.rules_engine import (
    rule_parcela_created, rule_parcela_without_active_ciclo,
    rule_ciclo_closed, rule_stage_advanced
)

@receiver(post_save, sender=Parcela)
def parcela_created_signal(sender, instance, created, **kwargs):
    if created:
        rule_parcela_created(instance)
        rule_parcela_without_active_ciclo(instance)

@receiver(post_save, sender=Ciclo)
def ciclo_saved_signal(sender, instance, created, **kwargs):
    if created:
        rule_parcela_without_active_ciclo(instance.parcela)
    else:
        if instance.estado == 'cerrado':
            rule_ciclo_closed(instance)
        # Si etapa cambió (puede compararse vía kwargs, aquí simplificado)
        rule_stage_advanced(instance)