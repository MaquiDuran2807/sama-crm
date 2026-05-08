import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Consulta mensajes de Evolution API y guarda el payload en JSON."

    def add_arguments(self, parser):
        parser.add_argument(
            "--instance",
            type=str,
            default=None,
            help="Nombre de la instancia de Evolution. Si se omite, intenta usar la primera disponible.",
        )
        parser.add_argument(
            "--from-timestamp",
            type=str,
            default=None,
            help="Timestamp ISO8601 para filtro incremental.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Cantidad maxima de mensajes solicitados.",
        )

    def handle(self, *args, **options):
        if not settings.EVOLUTION_API_KEY:
            raise CommandError("EVOLUTION_API_KEY no esta configurada en .env")

        instance_name = options["instance"] or self._resolve_first_instance()
        if not instance_name:
            raise CommandError(
                "No se encontro instancia. Pasa --instance o valida /instance/fetchInstances."
            )

        payload = self._fetch_messages(
            instance_name=instance_name,
            from_timestamp=options["from_timestamp"],
            limit=options["limit"],
        )

        output_path = self._save_payload(instance_name, payload)
        self.stdout.write(self.style.SUCCESS(f"JSON generado: {output_path}"))

    def _headers(self):
        return {
            "apikey": settings.EVOLUTION_API_KEY,
            "Content-Type": "application/json",
        }

    def _build_url(self, endpoint: str):
        return f"{settings.EVOLUTION_BASE_URL.rstrip('/')}{endpoint}"

    def _resolve_first_instance(self):
        url = self._build_url(settings.EVOLUTION_INSTANCES_ENDPOINT)
        response = requests.get(url, headers=self._headers(), timeout=20)
        response.raise_for_status()
        data = response.json()

        records = []
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            for key in ("instances", "data", "records", "result"):
                value = data.get(key)
                if isinstance(value, list):
                    records = value
                    break

        for record in records:
            if not isinstance(record, dict):
                continue
            name = (
                record.get("name")
                or record.get("instanceName")
                or record.get("instance")
                or record.get("instance_name")
            )
            if name:
                return name

        return None

    def _fetch_messages(self, instance_name: str, from_timestamp: str | None, limit: int):
        params = {"instance": instance_name, "limit": limit}
        if from_timestamp:
            params["fromTimestamp"] = from_timestamp
        query_body = {
            "where": {},
            "offset": limit,
            "page": 1,
        }
        if from_timestamp:
            query_body["where"]["messageTimestamp"] = {"gte": from_timestamp}

        endpoint_candidates = [
            ("POST", f"/chat/findMessages/{instance_name}", query_body, None),
            ("POST", f"/chat/findMessages/{instance_name}/", query_body, None),
            ("POST", "/chat/findMessages", query_body, params),
            ("POST", settings.EVOLUTION_MESSAGES_ENDPOINT, query_body, params),
            ("GET", settings.EVOLUTION_MESSAGES_ENDPOINT, None, params),
            ("GET", f"/message/findMessages/{instance_name}", None, params),
            ("GET", "/message/findMessages", None, params),
        ]

        attempts = []
        response = None
        used_endpoint = None
        used_method = None

        for method, endpoint, body, query_params in endpoint_candidates:
            url = self._build_url(endpoint)
            query = urlencode(query_params or {})
            attempts.append(f"{method} {url}{'?' + query if query else ''}")
            if method == "POST":
                candidate_response = requests.post(
                    url,
                    headers=self._headers(),
                    params=query_params,
                    json=body,
                    timeout=40,
                )
            else:
                candidate_response = requests.get(
                    url,
                    headers=self._headers(),
                    params=query_params,
                    timeout=40,
                )
            if candidate_response.status_code < 400:
                response = candidate_response
                used_endpoint = endpoint
                used_method = method
                break

        if response is None:
            raise CommandError(
                "No se pudo obtener mensajes. Endpoints probados:\n- " + "\n- ".join(attempts)
            )

        response.raise_for_status()

        return {
            "meta": {
                "fetched_at": datetime.utcnow().isoformat() + "Z",
                "base_url": settings.EVOLUTION_BASE_URL,
                "messages_method": used_method,
                "messages_endpoint": used_endpoint,
                "instance": instance_name,
                "params": params,
                "query_body": query_body,
                "attempts": attempts,
            },
            "payload": response.json(),
        }

    def _save_payload(self, instance_name: str, payload: dict):
        safe_instance = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in instance_name)
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        out_dir = Path(settings.BASE_DIR) / "data" / "evolution"
        out_dir.mkdir(parents=True, exist_ok=True)
        file_path = out_dir / f"messages_{safe_instance}_{timestamp}.json"

        with file_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        return file_path
