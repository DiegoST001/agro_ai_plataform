from rest_framework import serializers
from .models import Sensor
from .mongo import last_reading

class SensorSerializer(serializers.ModelSerializer):
    last_value = serializers.SerializerMethodField()
    class Meta:
        model = Sensor
        fields = ('id','nombre','tipo','unidad','node','parcela','last_value','created_at')
    def get_last_value(self, obj):
        doc = last_reading(obj.ext_collection, obj.ext_sensor_id)
        if not doc: return None
        return {'value': doc.get('value'), 'ts': doc.get('ts')}