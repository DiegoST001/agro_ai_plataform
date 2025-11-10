from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),

    # API apps
    path('api/', include('parcels.urls')),
    path('api/', include('plans.urls')),
    path('api/', include('recommendations.urls')),
    path('api/', include('nodes.urls')),
    path('api/', include('tasks.urls')),
    path('api/', include(('crops.urls', 'crops'), namespace='crops')),
    path('api/admin/', include('users.admin_urls')),
    path('api/rbac/', include('users.rbac_urls')),
    path('api/user/', include('users.user_urls')),
    path("api/ai/", include("ai.urls")),
    path('api/brain/', include('brain.urls')),

    # OpenAPI / docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Health checks (para evitar errores 400/404 en Render)
    path('', health_check),          # raíz /
    path('healthz/', health_check),  # endpoint explícito /healthz/
]
