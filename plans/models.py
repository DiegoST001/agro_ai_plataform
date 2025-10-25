from django.db import models
from datetime import datetime, time, timedelta
import pytz
from django.utils import timezone

class Plan(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    # Compatibilidad v1 (existente):
    frecuencia_minutos = models.IntegerField(null=True, blank=True)  # deprecado en favor de veces_por_dia/horarios
    # Nuevo v1.5:
    veces_por_dia = models.IntegerField(default=3)  # 3, 6 u 8
    horarios_por_defecto = models.JSONField(default=list)  # ["07:00","15:00","22:00"]
    limite_lecturas_dia = models.IntegerField(default=8)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'planes'  # coincide con tu script

    def __str__(self):
        return getattr(self, "nombre", f"Plan {self.id}")

    def get_schedule_for_date(self, date, tz=None):
        """
        Devuelve lista de datetimes (timezone-aware) programados para la fecha `date`.
        Precedencia: frecuencia_minutos > horarios_por_defecto > veces_por_dia.
        """
        tz = tz or timezone.get_current_timezone()
        date = date if isinstance(date, datetime) else datetime.combine(date, time.min)
        local_date = date.astimezone(tz) if date.tzinfo else tz.localize(date)

        scheduled = []

        # 1) frecuencia_minutos (legacy)
        if self.frecuencia_minutos:
            start = tz.localize(datetime.combine(local_date.date(), time(0, 0)))
            end = start + timedelta(days=1)
            curr = start
            delta = timedelta(minutes=int(self.frecuencia_minutos))
            while curr < end:
                scheduled.append(curr)
                curr += delta
            return scheduled

        # 2) horarios_por_defecto (lista de "HH:MM")
        if self.horarios_por_defecto:
            for hh in self.horarios_por_defecto:
                try:
                    h, m = map(int, hh.split(':'))
                    dt = tz.localize(datetime.combine(local_date.date(), time(h, m)))
                    scheduled.append(dt)
                except Exception:
                    continue
            return sorted(scheduled)

        # 3) veces_por_dia -> repartir en 24h (puedes ajustar entre amanecer/atardecer)
        if self.veces_por_dia and self.veces_por_dia > 0:
            interval = 24 * 60 // int(self.veces_por_dia)
            start = tz.localize(datetime.combine(local_date.date(), time(0, 0)))
            for i in range(int(self.veces_por_dia)):
                scheduled.append(start + timedelta(minutes=i * interval))
            return scheduled

        return scheduled


class ParcelaPlan(models.Model):
    ESTADOS = (
        ('activo', 'activo'),
        ('suspendido', 'suspendido'),
        ('vencido', 'vencido'),
    )
    parcela = models.ForeignKey('parcels.Parcela', on_delete=models.CASCADE, related_name='planes')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='parcelas')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'parcelas_planes'
        constraints = [
            models.UniqueConstraint(
                fields=['parcela'],
                condition=models.Q(estado='activo'),
                name='un_plan_activo_por_parcela'
            )
        ]

    def __str__(self):
        return f'{self.parcela_id} -> {self.plan.nombre} ({self.estado})'