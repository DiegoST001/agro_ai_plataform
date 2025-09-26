from django.shortcuts import render
from rest_framework import viewsets, permissions
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import AIIntegration
from .serializers import AIIntegrationSerializer

@extend_schema_view(
    list=extend_schema(tags=["Admin / AI Integrations"]),
    retrieve=extend_schema(tags=["Admin / AI Integrations"]),
    create=extend_schema(tags=["Admin / AI Integrations"]),
    update=extend_schema(tags=["Admin / AI Integrations"]),
    partial_update=extend_schema(tags=["Admin / AI Integrations"]),
    destroy=extend_schema(tags=["Admin / AI Integrations"]),
)
class AIIntegrationViewSet(viewsets.ModelViewSet):
    queryset = AIIntegration.objects.all()
    serializer_class = AIIntegrationSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        # Custom logic for AI integration can be added here
        serializer.save()

    def perform_update(self, serializer):
        # Custom logic for updating AI integration can be added here
        serializer.save()