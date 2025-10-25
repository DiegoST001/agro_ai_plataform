from django.db import models
from django.utils import timezone
from datetime import timedelta
from parcels.models import Parcela

class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

class Task(models.Model):
    AUTO_REJECT_DAYS = 3  # usado por procesos programados si se desea

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]

    DECISION_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aceptada', 'Aceptada'),
        ('rechazada', 'Rechazada'),
    ]

    ORIGEN_CHOICES = [
        ('manual', 'Manual'),
        ('ia', 'IA'),
    ]

    parcela = models.ForeignKey(Parcela, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=50)
    descripcion = models.TextField()
    fecha_programada = models.DateTimeField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')

    origen = models.CharField(max_length=10, choices=ORIGEN_CHOICES, default='manual')
    decision = models.CharField(max_length=10, choices=DECISION_CHOICES, default='pendiente')

    deleted_at = models.DateTimeField(null=True, blank=True)  # eliminación lógica
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # managers
    objects = ActiveManager()
    all_objects = models.Manager()

    def __str__(self):
        return f"Tarea {self.tipo} para {self.parcela.nombre}"

    def soft_delete(self):
        if self.deleted_at is None:
            self.deleted_at = timezone.now()
            self.save(update_fields=['deleted_at'])

    def restore(self):
        if self.deleted_at is not None:
            self.deleted_at = None
            self.save(update_fields=['deleted_at'])

    def accept(self):
        """
        Usuario acepta la recomendación (o confirma tarea manual).
        Para origen='ia' marca decision='aceptada'.
        """
        self.decision = 'aceptada'
        # No hacer soft-delete al aceptar; la tarea permanece activa
        self.save(update_fields=['decision', 'updated_at'])

    def reject(self, soft_delete_when_ia: bool = True):
        """
        Usuario rechaza la recomendación.
        Si la tarea vino de la IA y soft_delete_when_ia=True, se marca deleted_at (eliminación lógica).
        """
        self.decision = 'rechazada'
        self.save(update_fields=['decision', 'updated_at'])
        if soft_delete_when_ia and self.origen == 'ia':
            self.soft_delete()

    @classmethod
    def create_recommended(cls, parcela, tipo, descripcion, fecha_programada, snapshot=None, origen_id=None):
        """
        Crear una tarea sugerida por la IA.
        - origen='ia'
        - decision='pendiente' (usuario debe aceptar/rechazar)
        - opcional: incluir snapshot en la descripción o un campo externo si se desea
        """
        # Si se quiere preservar snapshot, podeis guardarlo dentro de descripcion o añadir JSONField.
        return cls.all_objects.create(
            parcela=parcela,
            tipo=tipo,
            descripcion=descripcion if descripcion is not None else "",
            fecha_programada=fecha_programada,
            estado='pendiente',
            origen='ia',
            decision='pendiente',
        )
