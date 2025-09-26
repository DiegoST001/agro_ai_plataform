from rest_framework import serializers
from .models import AlertRule, Alert

class AlertRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertRule
        fields = ('id','sensor','operador','umbral','activo','created_at')

class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = ('id','sensor','valor','mensaje','triggered_at','rule')