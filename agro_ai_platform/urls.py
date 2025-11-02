from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),

    # API apps
    path('api/', include('parcels.urls')),
    path('api/', include('plans.urls')),
    path('api/', include('recommendations.urls')),  # endpoints de recomendaciones
    path('api/', include('nodes.urls')),       # ingesta de nodos
    path('api/', include('tasks.urls')),       # endpoints de tareas

    # crops app (namespace y prefijo para evitar colisiones con otras apps)
    path('api/', include(('crops.urls', 'crops'), namespace='crops')),

    # admin / rbac / user
    path('api/admin/', include('users.admin_urls')),
    path('api/rbac/', include('users.rbac_urls')),
    path('api/user/', include('users.user_urls')),

    path("api/ai/", include("ai.urls")),
    path('api/brain/', include('brain.urls')),

    # OpenAPI / docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]