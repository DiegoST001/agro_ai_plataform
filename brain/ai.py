import os
import json
import http.client

GEMINI_MODEL = "gemini-1.5-flash"

def _build_prompt(meta: dict, points: list[dict]) -> str:
    return (
        "Eres un analista agrícola. Interpreta la serie temporal:\n"
        f"Sensor: {meta.get('parametro')}, Bucket: {meta.get('bucket')}, Puntos: {meta.get('points_count') or len(points)}\n"
        "Explica tendencias (sube/baja), promedios, picos, posibles causas y recomendaciones prácticas.\n"
        "Responde breve en español.\n"
        "Datos:\n" + json.dumps({"meta": meta, "points": points}, ensure_ascii=False)
    )

def summarize_timeseries(meta: dict, points: list[dict]) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not points:
        return None
    try:
        conn = http.client.HTTPSConnection("generativelanguage.googleapis.com", timeout=10)
        path = f"/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"
        body = { "contents": [ { "parts": [ { "text": _build_prompt(meta, points) } ] } ] }
        conn.request("POST", path, json.dumps(body), {"Content-Type": "application/json"})
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        conn.close()
        cand = (data.get("candidates") or [{}])[0]
        parts = cand.get("content", {}).get("parts") or []
        return parts[0].get("text") if parts and isinstance(parts[0], dict) else None
    except Exception:
        return None