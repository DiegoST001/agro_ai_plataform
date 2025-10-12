from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIChatView, AIIntegrationViewSet

router = DefaultRouter()
router.register(r'config', AIIntegrationViewSet, basename='aiintegration')

urlpatterns = [
    path("chat/", AIChatView.as_view(), name="chat"),
    path("", include(router.urls)),
]