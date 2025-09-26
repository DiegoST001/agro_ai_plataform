from django.db import models

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