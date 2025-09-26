import os
import subprocess
import json

try:
    import requests  # pip install requests
except Exception:  # lazy import fallback en runtime
    requests = None

OLLAMA_BIN = os.getenv("OLLAMA_BIN", "ollama")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

def _chat_via_cli(prompt: str, model: str) -> str:
    proc = subprocess.run(
        [OLLAMA_BIN, "run", model, prompt],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        # Propaga el error del CLI (modelo no descargado, etc.)
        raise RuntimeError(proc.stderr.strip() or "ollama cli error")
    return proc.stdout

def _chat_via_http(prompt: str, model: str, timeout: int = 120) -> str:
    if requests is None:
        raise RuntimeError("requests no instalado. Ejecuta: pip install requests")
    url = f"{OLLAMA_HOST.rstrip('/')}/api/generate"
    resp = requests.post(
        url,
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=timeout,
    )
    if resp.status_code != 200:
        # Intenta extraer mensaje de error JSON
        try:
            data = resp.json()
            msg = data.get("error") or data
        except Exception:
            msg = resp.text
        raise RuntimeError(f"ollama http error: {msg}")
    data = resp.json()
    # Respuesta típica: {"model":"...","created_at":"...","response":"texto","done":true,...}
    return data.get("response", "")

def chat(prompt: str, model: str = "llama3") -> str:
    # 1) Intento CLI primero (compatible con tus tests que mockean subprocess.run)
    try:
        return _chat_via_cli(prompt, model)
    except FileNotFoundError:
        # Binario no encontrado -> intenta HTTP
        return _chat_via_http(prompt, model)
    except RuntimeError as e_cli:
        # Si el CLI falla (ej. modelo no descargado), intenta HTTP para obtener un error más claro
        try:
            return _chat_via_http(prompt, model)
        except Exception:
            # Si HTTP también falla, relanza el error original del CLI
            raise e_cli