from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from ai_integration.views_ai import AIChatView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),
    path('api/', include('parcels.urls')),
    path('api/', include('plans.urls')),
    path('api/', include('nodes.urls')),       # <-- ingesta de nodos
    path('api/', include('sensors.urls')),     # si ya lo tienes
    path('api/', include('alerts.urls')),
    path('api/rbac/', include('users.urls')),  # gestión de permisos/roles

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # AI
    path('api/ai/chat/', AIChatView.as_view(), name='ai-chat'),
    path("api/ai/", include("ai.urls")),  # <-- OK con prefijo


]