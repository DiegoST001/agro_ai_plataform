from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

# Reglas disponibles en el motor
from recommendations.rules_engine import (
    rule_tasks_due,
    rule_stage_param_breach,
    rule_parcela_without_active_ciclo,
)
from parcels.models import Parcela


class Command(BaseCommand):
    help = "Evalúa reglas y genera alertas (tareas próximas, parcelas sin ciclo activo, parámetros fuera de rango)."

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=3, help='Días futuros para tareas próximas (default=3).')
        parser.add_argument(
            '--only',
            type=str,
            choices=['all', 'tasks', 'parcelas', 'sensors'],
            default='all',
            help="Selecciona qué reglas ejecutar (all|tasks|parcelas|sensors)."
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecuta las evaluaciones sin lanzar excepción si alguna regla falla (loggea y continúa).'
        )

    def handle(self, *args, **options):
        started = timezone.now()
        days = options['days']
        only = options['only']
        dry = options['dry_run']

        self.stdout.write(self.style.NOTICE(f"[generate_alerts] Inicio: {started.isoformat()}  (only={only}, days={days})"))

        def safe_run(label, fn):
            try:
                fn()
                self.stdout.write(self.style.SUCCESS(f"✔ {label} OK"))
            except Exception as exc:
                msg = f"✖ {label} ERROR: {exc}"
                if dry:
                    self.stderr.write(self.style.WARNING(msg))
                else:
                    raise CommandError(msg) from exc

        # Ejecutar reglas
        if only in ('all', 'tasks'):
            safe_run("Regla: tareas próximas a vencer", lambda: rule_tasks_due(days=days))

        if only in ('all', 'parcelas'):
            def run_parcelas_rules():
                # Parcela sin ciclo activo
                # Nota: upsert_alert en la regla maneja dedupe por fingerprint.
                for parcela in Parcela.objects.all().iterator():
                    rule_parcela_without_active_ciclo(parcela)
            safe_run("Regla: parcelas sin ciclo activo", run_parcelas_rules)

        if only in ('all', 'sensors'):
            safe_run("Regla: parámetros fuera de rango (sensores/etapas)", rule_stage_param_breach)

        finished = timezone.now()
        elapsed = (finished - started).total_seconds()
        self.stdout.write(self.style.SUCCESS(f"[generate_alerts] Fin: {finished.isoformat()}  (elapsed={elapsed:.2f}s)"))