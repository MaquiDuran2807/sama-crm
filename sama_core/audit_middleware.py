import json
import logging
import time
from typing import Callable

from django.http import HttpRequest, HttpResponse

audit_logger = logging.getLogger("sama.audit")


class AuditLogMiddleware:
    """Middleware que registra peticiones a la API en un log estructurado JSON.

    Captura timestamp, usuario, método, ruta, IP, User-Agent y duración.
    No registra bodys con datos sensibles (passwords, tokens).
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start = time.time()
        response = self.get_response(request)
        duration = time.time() - start

        if not request.path.startswith("/api/"):
            return response

        user = request.user
        audit_logger.info(
            json.dumps(
                {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "user": str(user) if user.is_authenticated else "anonymous",
                    "ip": request.META.get("REMOTE_ADDR", ""),
                    "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
                    "duration_ms": round(duration * 1000, 2),
                }
            )
        )
        return response
