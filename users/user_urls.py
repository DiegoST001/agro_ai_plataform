from django.urls import path
from .views import PerfilUsuarioView

urlpatterns = [
    path('profile/', PerfilUsuarioView.as_view(), name='profile'),
]