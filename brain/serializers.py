from rest_framework import serializers

class KPIEntrySerializer(serializers.Serializer):
    key = serializers.CharField()
    value = serializers.FloatField(required=False)
    meta = serializers.DictField(child=serializers.CharField(), required=False)

class KPISerializer(serializers.Serializer):
    scope = serializers.CharField()
    total_parcelas = serializers.IntegerField(required=False)
    parcelas_con_etapa = serializers.IntegerField(required=False)
    parcelas_sin_etapa = serializers.IntegerField(required=False)
    avg_tamano_hectareas = serializers.FloatField(required=False, allow_null=True)
    reglas_activas = serializers.IntegerField(required=False)
    reglas_relevantes = serializers.IntegerField(required=False)
    etapas_totales = serializers.IntegerField(required=False)
    parcelas_por_cultivo = serializers.ListField(child=serializers.DictField(), required=False)
    etapas_distribution = serializers.ListField(child=serializers.DictField(), required=False)

class TimeSeriesPointSerializer(serializers.Serializer):
    timestamp = serializers.CharField(allow_null=True)
    value = serializers.FloatField(allow_null=True)

class TimeSeriesResponseSerializer(serializers.Serializer):
    meta = serializers.DictField()
    points = serializers.ListField(child=TimeSeriesPointSerializer())

class DailyKPIItemSerializer(serializers.Serializer):
    nombre = serializers.CharField()
    dato = serializers.IntegerField(allow_null=True)

class DailyParcelKPISerializer(serializers.Serializer):
    parcela_id = serializers.IntegerField()
    fecha = serializers.CharField()
    kpis = serializers.ListField(child=DailyKPIItemSerializer())

class DailyUserKPISerializer(serializers.Serializer):
    usuario_id = serializers.IntegerField(required=False, allow_null=True)
    fecha = serializers.CharField()
    parcelas = serializers.ListField(child=DailyParcelKPISerializer())
    general = serializers.ListField(child=DailyKPIItemSerializer())