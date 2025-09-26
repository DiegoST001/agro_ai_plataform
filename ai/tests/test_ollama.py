from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
import subprocess

def test_ollama_chat_ok(db):
    User = get_user_model()
    u = User.objects.create_user(username="u1", password="p")
    client = APIClient()
    client.login(username="u1", password="p")

    with patch("ai.services.ollama.subprocess.run") as run:
        proc = MagicMock()
        proc.stdout = "hola"
        proc.returncode = 0
        proc.stderr = ""
        run.return_value = proc
        url = reverse("ollama-chat")
        resp = client.post(url, {"prompt": "ping"}, format="json")
        assert resp.status_code == 200
        assert resp.data["text"] == "hola"

def test_ollama_chat_error(db):
    User = get_user_model()
    u = User.objects.create_user(username="u2", password="p")
    client = APIClient()
    client.login(username="u2", password="p")

    with patch("ai.services.ollama.subprocess.run", side_effect=FileNotFoundError()):
        url = reverse("ollama-chat")
        resp = client.post(url, {"prompt": "ping"}, format="json")
        assert resp.status_code == 502