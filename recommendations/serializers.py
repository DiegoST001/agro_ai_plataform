from rest_framework import serializers
from .models import Recommendation

class RecommendationSerializer(serializers.ModelSerializer):
    parcela_id = serializers.IntegerField(source='parcela.id', read_only=True)

    class Meta:
        model = Recommendation
        fields = [
            'id', 'parcela_id', 'titulo', 'detalle', 'score',
            'source', 'tipo', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')