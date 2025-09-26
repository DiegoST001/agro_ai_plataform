from rest_framework import viewsets
from rest_framework.response import Response
from .models import Recomendaciones
from .serializers import RecomendacionesSerializer

class RecomendacionesViewSet(viewsets.ModelViewSet):
    queryset = Recomendaciones.objects.all()
    serializer_class = RecomendacionesSerializer

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)

    def retrieve(self, request, pk=None):
        queryset = self.get_queryset()
        recomendacion = self.get_object()
        serializer = self.get_serializer(recomendacion)
        return Response(serializer.data)

    def update(self, request, pk=None):
        recomendacion = self.get_object()
        serializer = self.get_serializer(recomendacion, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        recomendacion = self.get_object()
        self.perform_destroy(recomendacion)
        return Response(status=204)