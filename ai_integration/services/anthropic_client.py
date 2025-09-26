import json
import urllib.request
import urllib.error
from django.conf import settings

class AnthropicClient:
    """
    Minimal Anthropic Messages API client using urllib (no external deps).
    Targets global default model configured in settings.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL
        self.base_url = settings.ANTHROPIC_API_URL
        self.api_version = getattr(settings, 'ANTHROPIC_API_VERSION', '2023-06-01')
        if not self.api_key:
            raise ValueError('ANTHROPIC_API_KEY no configurada en entorno.')

    def chat(self, messages: list[dict], max_tokens: int = 512, temperature: float = 0.7) -> dict:
        """
        messages: list of {role: 'user'|'assistant'|'system', content: '...'}
        returns: dict with 'text' and 'raw'
        """
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            # Anthropic expects messages without a separate system param in older versions,
            # but the Messages API supports 'system' string and 'messages' list.
            # We'll extract a system message if provided.
        }
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        payload["messages"] = [m for m in messages if m.get("role") in ("user", "assistant")]

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(self.base_url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('x-api-key', self.api_key)
        req.add_header('anthropic-version', self.api_version)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode('utf-8'))
                # Extract assistant text
                text = ''
                try:
                    # body["content"][0]["text"] for Messages API
                    if isinstance(body.get('content'), list) and body['content']:
                        first = body['content'][0]
                        if isinstance(first, dict) and first.get('type') == 'text':
                            text = first.get('text', '')
                except Exception:
                    text = ''
                return {"text": text, "raw": body}
        except urllib.error.HTTPError as e:
            detail = e.read().decode('utf-8') if hasattr(e, 'read') else str(e)
            raise RuntimeError(f"Anthropic API error: {e.code} {detail}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Anthropic API connection error: {e}")
