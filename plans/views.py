from datetime import date
from django.shortcuts import render
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .models import Plan, ParcelaPlan
from .serializers import PlanSerializer
from parcels.models import Parcela
from users.permissions import HasOperationPermission
from .serializers import ParcelaPlanSerializer  # Asegúrate de que este serializer esté creado


@extend_schema(tags=['Planes'], summary='Listar planes')
class PlanListView(generics.ListAPIView):
    queryset = Plan.objects.all().order_by('precio')
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(tags=['Planes'], summary='Cambiar plan de una parcela')
class ParcelaChangePlanView(views.APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('planes', 'crear')]

    def post(self, request, parcela_id: int):
        plan_id = request.data.get('plan_id')
        if not plan_id:
            return Response({'detail': 'plan_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            parcela = Parcela.objects.get(id=parcela_id, usuario=request.user)
        except Parcela.DoesNotExist:
            return Response({'detail': 'Parcela no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            return Response({'detail': 'Plan no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        # Cerrar plan activo anterior si existe
        activo = ParcelaPlan.objects.filter(parcela=parcela, estado='activo').first()
        if activo:
            activo.estado = 'vencido'
            activo.fecha_fin = date.today()
            activo.save()

        # Crear nueva suscripción activa
        ParcelaPlan.objects.create(
            parcela=parcela,
            plan=plan,
            fecha_inicio=date.today(),
            estado='activo'
        )
        return Response({'detail': 'Plan actualizado.', 'parcela_id': parcela.id, 'plan_id': plan.id}, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Admin'],
    summary='Consultar el plan activo de una parcela',
    description='Devuelve el plan activo asociado a la parcela indicada.',
    responses=ParcelaPlanSerializer,
)
class ParcelaPlanDetailView(generics.RetrieveAPIView):
    serializer_class = ParcelaPlanSerializer

    def get_permissions(self):
        return [
            permissions.IsAuthenticated(),
            HasOperationPermission('administracion', 'ver')
        ]

    def get_object(self):
        parcela_id = self.kwargs.get('parcela_id')
        return ParcelaPlan.objects.filter(parcela_id=parcela_id, estado='activo').first()

# Create your views here.
