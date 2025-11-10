from django.db import models
from datetime import datetime, time, timedelta
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError

class Plan(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    # Nuevo v1.5: control por veces/hora explícita
    veces_por_dia = models.IntegerField(default=3)  # 3, 6 u 8
    horarios_por_defecto = models.JSONField(default=list, blank=True)  # ["07:00","15:00","22:00"]

    precio = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'planes'

    def __str__(self):
        return getattr(self, "nombre", f"Plan {self.id}")

    def clean(self):
        # validar horarios_por_defecto
        if self.horarios_por_defecto:
            if not isinstance(self.horarios_por_defecto, (list, tuple)):
                raise ValidationError({"horarios_por_defecto": "Debe ser una lista de strings 'HH:MM'."})
            cleaned = []
            for hh in self.horarios_por_defecto:
                if not isinstance(hh, str):
                    raise ValidationError({"horarios_por_defecto": "Cada elemento debe ser string 'HH:MM'."})
                try:
                    h, m = map(int, hh.split(':'))
                    if not (0 <= h < 24 and 0 <= m < 60):
                        raise ValueError
                    cleaned.append(f"{h:02d}:{m:02d}")
                except Exception:
                    raise ValidationError({"horarios_por_defecto": f"Formato inválido en '{hh}' (esperado 'HH:MM')."})
            self.horarios_por_defecto = list(dict.fromkeys(cleaned))
            # sincronizar veces_por_dia con horarios si difieren
            if self.veces_por_dia and int(self.veces_por_dia) != len(self.horarios_por_defecto):
                self.veces_por_dia = len(self.horarios_por_defecto)

        # validar veces_por_dia
        try:
            vp = int(self.veces_por_dia)
            if vp <= 0 or vp > 48:
                raise ValidationError({"veces_por_dia": "veces_por_dia fuera de rango razonable (>0)."})
        except (ValueError, TypeError):
            raise ValidationError({"veces_por_dia": "veces_por_dia debe ser entero."})

    def save(self, *args, **kwargs):
        self.clean()
        # si no hay horarios explícitos, generar horarios prácticos entre 06:00 y 22:00
        if (not self.horarios_por_defecto) and (self.veces_por_dia and int(self.veces_por_dia) > 0):
            vp = int(self.veces_por_dia)
            start_hour = 6
            end_hour = 22
            total_minutes = max(1, (end_hour - start_hour) * 60)
            interval = total_minutes // vp if vp > 0 else 0
            generated = []
            for i in range(vp):
                minutes = start_hour * 60 + i * interval
                h = (minutes // 60) % 24
                m = minutes % 60
                generated.append(f"{h:02d}:{m:02d}")
            self.horarios_por_defecto = list(dict.fromkeys(generated))
        super().save(*args, **kwargs)

    def get_schedule_for_date(self, date, tz=None):
        tz = tz or timezone.get_current_timezone()
        target_date = date.date() if isinstance(date, datetime) else date

        def make_dt(h, m):
            naive = datetime.combine(target_date, time(int(h), int(m)))
            return timezone.make_aware(naive, tz)

        scheduled = []
        if self.horarios_por_defecto:
            for hh in self.horarios_por_defecto:
                try:
                    h, m = map(int, hh.split(':'))
                    scheduled.append(make_dt(h, m))
                except Exception:
                    continue
            return sorted(dict.fromkeys(scheduled))

        # fallback: repartir por veces_por_dia si no hay horarios (no debería ocurrir porque save genera horarios)
        try:
            vp = int(self.veces_por_dia or 0)
            if vp > 0:
                interval_minutes = (24 * 60) / vp
                for i in range(vp):
                    minutes = int(round(i * interval_minutes))
                    h = (minutes // 60) % 24
                    m = minutes % 60
                    scheduled.append(make_dt(h, m))
                return sorted(dict.fromkeys(scheduled))
        except Exception:
            pass

        return []


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

    def save(self, *args, **kwargs):
        # ParcelaPlan no debe generar o manipular horarios del Plan.
        # La lógica de generación/validación de horarios vive en Plan.save().
        super().save(*args, **kwargs)