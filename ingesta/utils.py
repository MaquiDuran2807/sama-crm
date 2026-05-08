import requests
from django.conf import settings


def get_ollama_client(prompt: str = "Responde solo: conexion_ok") -> dict:
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    response = requests.post(url, json=payload, timeout=20)
    response.raise_for_status()
    data = response.json()
    return {
        "ok": True,
        "model": settings.OLLAMA_MODEL,
        "response": data.get("response", "").strip(),
    }
