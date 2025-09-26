from django.shortcuts import render
from rest_framework import viewsets
from .models import AIIntegration
from .serializers import AIIntegrationSerializer

class AIIntegrationViewSet(viewsets.ModelViewSet):
    queryset = AIIntegration.objects.all()
    serializer_class = AIIntegrationSerializer

    def perform_create(self, serializer):
        # Custom logic for AI integration can be added here
        serializer.save()

    def perform_update(self, serializer):
        # Custom logic for updating AI integration can be added here
        serializer.save()