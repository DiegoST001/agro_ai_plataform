from django.urls import path
from .views import (
    PerfilUsuarioView,
    ProspectoListView,
    ProspectoDetailView,
    ProspectoAceptarView,
    UsuariosTotalPublicView,
    ProspectoPublicCreateView,
    ChangePasswordView,
    AdminUserPasswordUpdateView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)

urlpatterns = [
    path('profile/', PerfilUsuarioView.as_view(), name='profile'),
    path('password/change/', ChangePasswordView.as_view(), name='password-change'),
    path('admin/users/<int:user_id>/password/', AdminUserPasswordUpdateView.as_view(), name='admin-user-password'),
    path('prospectos/', ProspectoListView.as_view(), name='prospecto-list'),
    path('prospectos/<int:pk>/', ProspectoDetailView.as_view(), name='prospecto-detail'),  # <-- Detalle del prospecto
    path('prospectos/<int:pk>/aceptar/', ProspectoAceptarView.as_view(), name='prospecto-aceptar'),
    path('total/public/', UsuariosTotalPublicView.as_view(), name='usuarios-total-public'),
    path('prospectos/public/', ProspectoPublicCreateView.as_view(), name='prospecto-public-create'),  # <-- nueva ruta pública
    path('password/reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]