from rest_framework import generics, permissions
from .models import AlertRule, Alert
from .serializers import AlertRuleSerializer, AlertSerializer
from users.permissions import HasOperationPermission

class AlertRuleListCreateView(generics.ListCreateAPIView):
    serializer_class = AlertRuleSerializer
    filterset_fields = ['sensor','activo']
    def get_queryset(self):
        return AlertRule.objects.filter(sensor__parcela__usuario=self.request.user)
    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('alertas', 'crear' if self.request.method=='POST' else 'ver')]

class AlertListView(generics.ListAPIView):
    serializer_class = AlertSerializer
    filterset_fields = ['sensor']
    ordering = ['-triggered_at']
    def get_queryset(self):
        return Alert.objects.filter(sensor__parcela__usuario=self.request.user)
    def get_permissions(self):
        return [permissions.IsAuthenticated(), HasOperationPermission('alertas', 'ver')]