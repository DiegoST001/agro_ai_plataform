from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from drf_spectacular.utils import extend_schema
from .services import compute_kpis_for_user, aggregate_timeseries, fetch_history
from .serializers import KPISerializer, TimeSeriesResponseSerializer
from users.permissions import tiene_permiso

@extend_schema(
    tags=['brain'],
    summary='KPIs del sistema / usuario',
    description=(
        "Devuelve KPIs resumidos.\n\n"
        "- Si el usuario es administrador/superadmin devuelve KPIs globales.\n"
        "- Si es agricultor devuelve KPIs limitados a sus parcelas.\n\n"
        "Requiere estar autenticado y tener permiso de lectura de parcelas (parcelas.ver)."
    ),
    responses={200: KPISerializer()}
)
class KPIsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        # requisito base: al menos permiso para ver parcelas
        if not tiene_permiso(user, 'parcelas', 'ver'):
            raise PermissionDenied(detail="No tiene permiso para ver KPIs (se requiere parcelas.ver).")
        kpis = compute_kpis_for_user(user)
        return Response(kpis, status=status.HTTP_200_OK)

class TimeSeriesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['brain'],
        summary='Serie temporal para parámetro de parcela',
        description=(
            "Devuelve puntos agregados (avg) para un parámetro de una parcela.\n\n"
            "Query params:\n"
            "- parcela (required)\n"
            "- parametro (required)\n"
            "- period (optional): hour|day|week|month|year (ventana por defecto)\n"
            "- interval (optional): minute|hour|day|month|year (bucket)\n"
            "- start, end (ISO datetimes opcionales) para ventana personalizada\n\n"
            "Si no se pasa start/end se calcula la ventana en base a 'period'."
        ),
        responses={200: TimeSeriesResponseSerializer()}
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        if not tiene_permiso(user, 'parcelas', 'ver'):
            raise PermissionDenied(detail="No tiene permiso para ver series (se requiere parcelas.ver).")

        parcela = request.query_params.get('parcela')
        parametro = request.query_params.get('parametro')
        period = request.query_params.get('period', 'day')
        interval = request.query_params.get('interval')
        start = request.query_params.get('start')
        end = request.query_params.get('end')

        if not parcela or not parametro:
            raise ValidationError({"detail": "parcela y parametro son requeridos."})

        from django.utils.dateparse import parse_datetime
        start_dt = parse_datetime(start) if start else None
        end_dt = parse_datetime(end) if end else None

        try:
            data = aggregate_timeseries(int(parcela), parametro, period=period, interval=interval, start=start_dt, end=end_dt)
        except Exception as e:
            raise ValidationError({"detail": str(e)})

        return Response(data, status=status.HTTP_200_OK)

class HistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['brain'],
        summary='Historial de lecturas (agrupado)',
        description=(
            "Devuelve el historial de lecturas para una parcela agrupado por periodo.\n\n"
            "Query params:\n"
            "- parcela (required)\n"
            "- period (required): hour|day|week|month|year\n"
            "- parametro (optional): filtrar por sensor (ej. 'humedad')\n"
            "- start/end (ISO datetimes opcionales) para ventana personalizada\n"
        ),
        responses={200: TimeSeriesResponseSerializer()}
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        if not tiene_permiso(user, 'parcelas', 'ver'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(detail="No tiene permiso para ver historial (parcelas.ver requerido).")

        parcela = request.query_params.get('parcela')
        period = request.query_params.get('period')
        parametro = request.query_params.get('parametro')
        start = request.query_params.get('start')
        end = request.query_params.get('end')

        if not parcela or not period:
            raise ValidationError({"detail": "parcela y period son requeridos."})

        from django.utils.dateparse import parse_datetime
        start_dt = parse_datetime(start) if start else None
        end_dt = parse_datetime(end) if end else None

        try:
            data = fetch_history(int(parcela), period=period, parametro=parametro, start=start_dt, end=end_dt)
        except Exception as e:
            raise ValidationError({"detail": str(e)})

        return Response(data, status=status.HTTP_200_OK)
