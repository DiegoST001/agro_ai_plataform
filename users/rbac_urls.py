from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import RolViewSet, ModuloViewSet, RolesOperacionesViewSet, UserRoleUpdateView

router = SimpleRouter()
router.register(r'roles', RolViewSet, basename='rbac-roles')
router.register(r'modulos', ModuloViewSet, basename='rbac-modulos')
router.register(r'permissions', RolesOperacionesViewSet, basename='rbac-permissions')

urlpatterns = [
    path('', include(router.urls)),
    path('users/<int:user_id>/role/', UserRoleUpdateView.as_view(), name='rbac-user-role'),
]