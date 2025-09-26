from django.urls import path
from .views import OllamaChatView

urlpatterns = [
    path("ollama/chat/", OllamaChatView.as_view(), name="ollama-chat"),
]