from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),
    path('api/', include('parcels.urls')),
    path('api/', include('plans.urls')),
    path('api/', include('recommendations.urls')),  # agregado: endpoints de recomendaciones (ajusta a 'recomendaciones' si tu app usa nombre en español)
    path('api/', include('nodes.urls')),       # ingesta de nodos
    path('api/', include('tasks.urls')),       # agregado: endpoints de tareas
    # path('api/', include('alerts.urls')),
    path('api/admin/', include('users.admin_urls')),    # gestión de usuarios y recursos admin
    path('api/rbac/', include('users.rbac_urls')),      # gestión de roles/permisos
    path('api/user/', include('users.user_urls')),  # endpoints para clientes (perfil, etc.)

    path("api/ai/", include("ai.urls")),  # AI endpoints

    # agregar brain API
    path('api/brain/', include('brain.urls')),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]