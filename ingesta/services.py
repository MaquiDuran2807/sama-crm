from datetime import datetime, timedelta, timezone as dt_timezone
import base64
import os
import threading
from urllib.parse import urlparse

import pandas as pd
import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import ChatUser, EvolutionInstance, IngestionControl, Message


class IngestionService:
    def __init__(self, instance_name: str = "default"):
        self.instance_name = (instance_name or "default").strip()

    def sync_messages(self, progress_callback=None) -> dict:
        # Obtener instancia de Evolution
        try:
            instance = EvolutionInstance.objects.get(instance_name=self.instance_name)
        except EvolutionInstance.DoesNotExist:
            raise ValueError(
                f"Instancia '{self.instance_name}' no encontrada. "
                f"Instancias disponibles: {', '.join(EvolutionInstance.objects.filter(is_active=True).values_list('instance_name', flat=True))}"
            )

        self._notify(progress_callback, 5, "Iniciando sincronizacion incremental")
        
        # Obtener o crear control de ingesta
        control, _ = IngestionControl.objects.get_or_create(
            instance=instance,
            defaults={"last_sync_timestamp": datetime(1970, 1, 1, tzinfo=dt_timezone.utc)},
        )
        last_sync = control.last_sync_timestamp
        cursor_timestamp = int(last_sync.timestamp())
        overlap_hours = max(0, int(getattr(settings, "EVOLUTION_SYNC_OVERLAP_HOURS", 6)))
        effective_cursor_timestamp = max(0, cursor_timestamp - (overlap_hours * 3600))
        cutoff_dt = datetime.fromtimestamp(effective_cursor_timestamp, tz=dt_timezone.utc)

        self._notify(
            progress_callback,
            12,
            f"Cursor actual: {last_sync.isoformat()} (epoch={cursor_timestamp})",
        )
        self._notify(
            progress_callback,
            13,
            f"Ventana incremental: solape={overlap_hours}h | cutoff={cutoff_dt.isoformat()} (epoch={effective_cursor_timestamp})",
        )
        self._notify(progress_callback, 14, f"Instancia activa: {self.instance_name}")

        page_size = int(getattr(settings, "EVOLUTION_PAGE_SIZE", 200))
        max_pages = int(getattr(settings, "EVOLUTION_MAX_PAGES_PER_SYNC", 50))
        page = 1
        all_records = []
        total_pages_hint = None
        stale_pages_to_stop = max(1, int(getattr(settings, "EVOLUTION_STOP_AFTER_STALE_PAGES", 2)))
        consecutive_stale_pages = 0

        while page <= max_pages:
            payload = self._fetch_messages_page(
                cursor_timestamp=effective_cursor_timestamp,
                page=page,
                page_size=page_size,
            )
            records, current_page, pages_total = self._extract_page_bundle(payload)

            if total_pages_hint is None:
                total_pages_hint = pages_total

            if not records:
                break

            page_newer_count = 0
            for record in records:
                raw_ts = record.get("messageTimestamp") or record.get("timestamp") or record.get("time")
                try:
                    record_ts = int(raw_ts)
                except (TypeError, ValueError):
                    record_ts = 0
                if record_ts > effective_cursor_timestamp:
                    page_newer_count += 1

            if page_newer_count == 0:
                consecutive_stale_pages += 1
            else:
                consecutive_stale_pages = 0

            all_records.extend(records)

            progress = 12
            if pages_total and pages_total > 0:
                progress = min(68, 12 + int((current_page / pages_total) * 56))
            self._notify(
                progress_callback,
                progress,
                f"Descargando paginas: {current_page}/{pages_total} - acumulado {len(all_records)} (nuevos_en_pagina={page_newer_count})",
            )

            if consecutive_stale_pages >= stale_pages_to_stop:
                self._notify(
                    progress_callback,
                    progress,
                    f"Detenido por paginas sin nuevos respecto al cutoff ({consecutive_stale_pages}/{stale_pages_to_stop})",
                )
                break

            if current_page >= pages_total:
                break
            page += 1

        self._notify(
            progress_callback,
            70,
            f"Descarga completada: {len(all_records)} registros totales recibidos",
        )

        if not all_records:
            self._notify(progress_callback, 100, "No hay nuevos mensajes en el rango incremental")
            return {
                "instance_name": self.instance_name,
                "pages_fetched": page - 1,
                "fetched": 0,
                "deduplicated": 0,
                "inserted": 0,
                "last_sync_timestamp": last_sync.isoformat(),
            }

        df = pd.DataFrame(all_records)
        if df.empty:
            self._notify(progress_callback, 100, "Payload vacio tras convertir a DataFrame")
            return {
                "instance_name": self.instance_name,
                "pages_fetched": page - 1,
                "fetched": 0,
                "deduplicated": 0,
                "inserted": 0,
                "last_sync_timestamp": last_sync.isoformat(),
            }

        df["external_id"] = df.apply(self._build_external_id, axis=1)
        df["wa_id"] = df.apply(self._extract_wa_id, axis=1)
        df["name"] = df.apply(self._extract_name, axis=1)
        df["phone_number"] = df.apply(self._extract_phone_number, axis=1)
        df["from_me"] = df.apply(self._extract_from_me, axis=1)
        df["direction"] = df.apply(self._extract_direction, axis=1)
        df["chat_jid"] = df.apply(self._extract_chat_jid, axis=1)
        df["sender_wa_id"] = df.apply(self._extract_sender_wa_id, axis=1)
        df["recipient_wa_id"] = df.apply(self._extract_recipient_wa_id, axis=1)
        df["quoted_external_id"] = df.apply(self._extract_quoted_external_id, axis=1)
        df["media_url"] = df.apply(self._extract_media_url, axis=1)
        df["media_mime_type"] = df.apply(self._extract_media_mime_type, axis=1)
        df["content"] = df.apply(self._extract_content, axis=1)
        df["message_type"] = df.apply(self._extract_type, axis=1)
        df["timestamp"] = df.apply(self._extract_timestamp, axis=1)
        df["raw_data"] = all_records

        df = df[df["external_id"].notna() & df["wa_id"].notna()].copy()
        before_cutoff = len(df)
        df = df[df["timestamp"] > cutoff_dt].copy()
        dropped_by_cutoff = before_cutoff - len(df)
        df = df[~df["chat_jid"].astype(str).str.lower().eq("status@broadcast")].copy()
        df = df[~df["chat_jid"].astype(str).str.endswith("@g.us", na=False)].copy()
        self._notify(
            progress_callback,
            78,
            f"Normalizados: {len(df)} validos | descartados_por_cutoff={dropped_by_cutoff} | sin grupos/status",
        )

        if df.empty:
            self._notify(progress_callback, 100, "No hubo registros validos para procesar")
            return {
                "instance_name": self.instance_name,
                "pages_fetched": page - 1,
                "fetched": len(all_records),
                "deduplicated": len(all_records),
                "inserted": 0,
                "last_sync_timestamp": last_sync.isoformat(),
            }

        existing_ids = set(
            Message.objects.filter(external_id__in=df["external_id"].tolist()).values_list(
                "external_id", flat=True
            )
        )
        df_new = df[~df["external_id"].isin(existing_ids)].copy()

        self._notify(
            progress_callback,
            86,
            f"Deduplicacion: nuevos={len(df_new)} | repetidos={len(df) - len(df_new)}",
        )

        wa_ids = df["wa_id"].dropna().unique().tolist()
        user_by_wa = {u.wa_id: u for u in ChatUser.objects.filter(wa_id__in=wa_ids)}
        wa_ids_by_user_id = {}
        for wa, user in user_by_wa.items():
            wa_ids_by_user_id.setdefault(user.id, set()).add(wa)

        phone_numbers = [
            str(p).strip()
            for p in df["phone_number"].dropna().astype(str).unique().tolist()
            if str(p).strip()
        ]
        user_by_phone = {
            u.phone_number: u
            for u in ChatUser.objects.filter(phone_number__in=phone_numbers).exclude(phone_number="")
        }

        missing_wa_ids = [wa for wa in wa_ids if wa not in user_by_wa]
        users_to_create = []
        for wa_id in missing_wa_ids:
            subset = df[df["wa_id"] == wa_id]
            first_row = subset.iloc[0]
            phone_number = str(first_row.get("phone_number") or "").strip()

            existing_user = user_by_phone.get(phone_number) if phone_number else None
            if existing_user:
                user_by_wa[wa_id] = existing_user
                wa_ids_by_user_id.setdefault(existing_user.id, set()).add(wa_id)
                continue

            safe_name = self._pick_best_contact_name(subset)
            users_to_create.append(
                ChatUser(
                    wa_id=wa_id,
                    name=safe_name,
                    phone_number=phone_number,
                    last_interaction=first_row["timestamp"],
                )
            )
        if users_to_create:
            ChatUser.objects.bulk_create(users_to_create, ignore_conflicts=True)
            user_by_wa = {u.wa_id: u for u in ChatUser.objects.filter(wa_id__in=wa_ids)}
            wa_ids_by_user_id = {}
            for wa, user in user_by_wa.items():
                wa_ids_by_user_id.setdefault(user.id, set()).add(wa)

            for wa_id in missing_wa_ids:
                if wa_id in user_by_wa:
                    continue
                subset = df[df["wa_id"] == wa_id]
                if subset.empty:
                    continue
                phone_number = str(subset.iloc[0].get("phone_number") or "").strip()
                existing_user = user_by_phone.get(phone_number) if phone_number else None
                if existing_user:
                    user_by_wa[wa_id] = existing_user
                    wa_ids_by_user_id.setdefault(existing_user.id, set()).add(wa_id)

        users_to_update = []
        seen_user_ids = set()
        for wa_id, user in user_by_wa.items():
            if user.id in seen_user_ids:
                continue
            seen_user_ids.add(user.id)

            mapped_wa_ids = wa_ids_by_user_id.get(user.id) or {wa_id}
            subset = df[df["wa_id"].isin(list(mapped_wa_ids))]
            if subset.empty:
                continue
            newest_ts = subset["timestamp"].max()
            newest_name = self._pick_best_contact_name(subset)
            changed = False
            if newest_ts and newest_ts > user.last_interaction:
                user.last_interaction = newest_ts
                changed = True
            # Conserva el nombre manual existente; solo completa cuando no hay nombre.
            if newest_name and not str(user.name or "").strip():
                user.name = newest_name
                changed = True
            newest_phone = str(subset["phone_number"].dropna().astype(str).iloc[-1]).strip() if subset["phone_number"].notna().any() else ""
            if newest_phone and newest_phone != user.phone_number:
                user.phone_number = newest_phone
                changed = True
            if changed:
                users_to_update.append(user)
        if users_to_update:
            ChatUser.objects.bulk_update(users_to_update, ["name", "phone_number", "last_interaction"])

        messages_to_insert = []
        for row in df_new.to_dict("records"):
            user = user_by_wa.get(row["wa_id"])
            if not user:
                continue

            media_url = str(row.get("media_url") or "").strip()
            media_mime_type = str(row.get("media_mime_type") or "").strip()

            messages_to_insert.append(
                Message(
                    external_id=row["external_id"],
                    user=user,
                    content=row.get("content", ""),
                    from_me=bool(row.get("from_me", False)),
                    direction=row.get("direction", Message.Direction.INBOUND),
                    chat_jid=str(row.get("chat_jid") or "").strip(),
                    sender_wa_id=str(row.get("sender_wa_id") or "").strip(),
                    recipient_wa_id=str(row.get("recipient_wa_id") or "").strip(),
                    quoted_external_id=str(row.get("quoted_external_id") or "").strip(),
                    media_url=media_url,
                    media_file=None,
                    media_mime_type=media_mime_type,
                    message_type=row.get("message_type", Message.MessageType.OTHER),
                    raw_data=row.get("raw_data", {}),
                    timestamp=row["timestamp"],
                    processed=False,
                )
            )

        inserted = 0
        max_ts = df["timestamp"].max() if not df.empty else None
        with transaction.atomic():
            if messages_to_insert:
                created = Message.objects.bulk_create(messages_to_insert, ignore_conflicts=True)
                inserted = len(created)

            if max_ts:
                control.last_sync_timestamp = max_ts
                control.save(update_fields=["last_sync_timestamp"])

        self._notify(progress_callback, 100, f"Sincronizacion finalizada: {inserted} insertados")

        media_types = [Message.MessageType.AUDIO, Message.MessageType.IMAGE, Message.MessageType.VIDEO]
        if df_new[df_new["message_type"].isin(media_types)].shape[0] > 0:
            threading.Thread(
                target=self._download_media_files_async,
                args=(df_new[df_new["message_type"].isin(media_types)],),
                daemon=True,
            ).start()

        return {
            "instance_name": self.instance_name,
            "pages_fetched": page,
            "fetched": len(df),
            "deduplicated": len(df) - len(df_new),
            "inserted": inserted,
            "last_sync_timestamp": control.last_sync_timestamp.isoformat(),
        }

    def _fetch_messages_page(self, cursor_timestamp: int, page: int, page_size: int) -> dict:
        headers = {"Content-Type": "application/json"}
        if settings.EVOLUTION_API_KEY:
            headers["apikey"] = settings.EVOLUTION_API_KEY

        where_clause = {}
        if cursor_timestamp > 0:
            where_clause = {"messageTimestamp": {"gt": cursor_timestamp}}

        body = {
            "where": where_clause,
            "offset": page_size,
            "page": page,
        }

        configured = getattr(settings, "EVOLUTION_MESSAGES_ENDPOINT", "/chat/findMessages")
        configured = configured.strip()
        if "{instance}" in configured:
            configured = configured.replace("{instance}", self.instance_name)

        candidates = []
        candidates.extend(
            [
                f"/chat/findMessages/{self.instance_name}",
                "/chat/findMessages",
            ]
        )
        if configured:
            if configured.endswith(f"/{self.instance_name}"):
                candidates.append(configured)
            else:
                candidates.append(configured)
                candidates.append(f"{configured.rstrip('/')}/{self.instance_name}")
        candidates = list(dict.fromkeys(candidates))

        attempts = []
        last_error = None
        for endpoint in candidates:
            url = f"{settings.EVOLUTION_BASE_URL.rstrip('/')}{endpoint}"
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    params={"instance": self.instance_name},
                    json=body,
                    timeout=40,
                )
                if response.status_code < 400:
                    return response.json()
                preview = (response.text or "").strip().replace("\n", " ")
                if len(preview) > 180:
                    preview = preview[:180] + "..."
                attempt_msg = f"{response.status_code} en {url} | body={preview or 'vacio'}"
                attempts.append(attempt_msg)
                last_error = attempt_msg
            except requests.RequestException as exc:
                attempt_msg = f"EXC en {url} | {exc}"
                attempts.append(attempt_msg)
                last_error = attempt_msg

        attempts_text = " ; ".join(attempts) if attempts else str(last_error)
        raise requests.HTTPError(f"No se pudo consultar Evolution API. Intentos: {attempts_text}")

    def _resolve_instance_name(self) -> str | None:
        headers = {"Content-Type": "application/json"}
        if settings.EVOLUTION_API_KEY:
            headers["apikey"] = settings.EVOLUTION_API_KEY

        endpoint = getattr(settings, "EVOLUTION_INSTANCES_ENDPOINT", "/instance/fetchInstances")
        url = f"{settings.EVOLUTION_BASE_URL.rstrip('/')}{endpoint}"
        response = requests.get(url, headers=headers, timeout=20)
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
                return str(name)
        return None

    @staticmethod
    def _extract_page_bundle(payload: dict) -> tuple[list, int, int]:
        if isinstance(payload, dict):
            messages = payload.get("messages")
            if isinstance(messages, dict):
                records = messages.get("records") or []
                current_page = int(messages.get("currentPage") or 1)
                pages_total = int(messages.get("pages") or 1)
                return records, current_page, pages_total

            for key in ("records", "data", "results"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value, 1, 1

        if isinstance(payload, list):
            return payload, 1, 1

        return [], 1, 1

    @staticmethod
    def _build_external_id(row) -> str | None:
        return row.get("id") or row.get("messageId") or row.get("key", {}).get("id")

    @staticmethod
    def _extract_wa_id(row) -> str | None:
        key = row.get("key", {}) if isinstance(row.get("key"), dict) else {}
        remote_jid = key.get("remoteJidAlt") or key.get("remoteJid") or row.get("wa_id") or row.get("from") or row.get("sender")
        participant_jid = (
            key.get("participantAlt")
            or key.get("participant")
            or row.get("participantAlt")
            or row.get("participant")
        )

        remote_jid = str(remote_jid or "").strip() or None
        participant_jid = str(participant_jid or "").strip() or None

        if remote_jid and remote_jid.endswith("@g.us"):
            return participant_jid or remote_jid

        if remote_jid and remote_jid.endswith("@lid") and participant_jid:
            return participant_jid

        return participant_jid or remote_jid

    @staticmethod
    def _extract_name(row) -> str:
        from_me = IngestionService._extract_from_me(row)
        for field in ("pushName", "name", "senderName", "profileName", "verifiedName", "contactName"):
            value = row.get(field)
            if value:
                label = str(value).strip()
                if from_me and IngestionService._is_generic_self_label(label):
                    continue
                if label and not IngestionService._is_name_like_number(label):
                    return label

        return ""

    @staticmethod
    def _extract_phone_number(row) -> str:
        wa_id = IngestionService._extract_wa_id(row)
        if not wa_id:
            return ""

        wa_id = str(wa_id).strip()
        if "@" in wa_id:
            return wa_id.split("@", 1)[0].strip()
        return wa_id

    @staticmethod
    def _extract_chat_jid(row) -> str:
        key = row.get("key", {}) if isinstance(row.get("key"), dict) else {}
        chat_jid = (
            key.get("remoteJidAlt")
            or key.get("remoteJid")
            or row.get("remoteJidAlt")
            or row.get("remoteJid")
            or row.get("chatJid")
            or row.get("chat_jid")
            or ""
        )
        return str(chat_jid).strip()

    @staticmethod
    def _extract_media_payload(row) -> dict:
        message = row.get("message") if isinstance(row.get("message"), dict) else {}
        if not message:
            return {}

        for key in (
            "audioMessage",
            "pttMessage",
            "voiceMessage",
            "imageMessage",
            "videoMessage",
            "documentMessage",
        ):
            payload = message.get(key)
            if isinstance(payload, dict):
                return payload

        for key, value in message.items():
            if isinstance(value, dict) and any(token in key.lower() for token in ("audio", "voice", "ptt")):
                return value

        return {}

    @staticmethod
    def _extract_media_url(row) -> str:
        payload = IngestionService._extract_media_payload(row)
        media_url = payload.get("url") or payload.get("mediaUrl") or row.get("mediaUrl") or row.get("media_url")
        media_url = str(media_url or "").strip()
        if media_url.startswith("http://") or media_url.startswith("https://"):
            return media_url
        return ""

    @staticmethod
    def _extract_media_mime_type(row) -> str:
        payload = IngestionService._extract_media_payload(row)
        mime_type = payload.get("mimetype") or payload.get("mimeType") or row.get("mimetype") or row.get("mimeType")
        return str(mime_type or "").strip()

    def _download_media_file(
        self,
        external_id: str,
        media_url: str,
        media_mime_type: str,
        raw_data: dict | None = None,
        debug_info: dict | None = None,
    ) -> str:
        if debug_info is None:
            debug_info = {}
        if not media_url:
            debug_info.update({"phase": "precheck", "error": "NO_MEDIA_URL"})
            return ""

        parsed_path = urlparse(media_url).path.lower()
        if parsed_path.endswith(".enc"):
            debug_info.update({"phase": "decode_enc", "is_enc": True})
            decoded = self._fetch_decoded_media_from_evolution(raw_data or {}, debug_info=debug_info)
            if not decoded:
                return ""
            decoded_bytes, file_name, decoded_mime_type = decoded
            extension = os.path.splitext(file_name or "")[1] or self._guess_media_extension(media_url, decoded_mime_type or media_mime_type)
            relative_path = f"ingesta/media/{external_id}{extension}"
            if default_storage.exists(relative_path):
                debug_info.update({"phase": "save", "result": "already_exists"})
                return relative_path
            default_storage.save(relative_path, ContentFile(decoded_bytes))
            debug_info.update({"phase": "save", "result": "saved"})
            return relative_path

        extension = IngestionService._guess_media_extension(media_url, media_mime_type)
        relative_path = f"ingesta/media/{external_id}{extension}"

        if default_storage.exists(relative_path):
            debug_info.update({"phase": "save", "result": "already_exists"})
            return relative_path

        try:
            debug_info.update({"phase": "download_direct", "is_enc": False})
            response = requests.get(media_url, timeout=40)
            debug_info["http_status"] = response.status_code
            response.raise_for_status()
            default_storage.save(relative_path, ContentFile(response.content))
            debug_info.update({"phase": "save", "result": "saved"})
            return relative_path
        except requests.RequestException as ex:
            debug_info.update(
                {
                    "error": "DIRECT_DOWNLOAD_REQUEST_FAILED",
                    "exception_type": type(ex).__name__,
                    "exception": str(ex),
                }
            )
            return ""

    def _fetch_decoded_media_from_evolution(self, raw_data: dict, debug_info: dict | None = None) -> tuple[bytes, str, str] | None:
        if debug_info is None:
            debug_info = {}
        if not raw_data:
            debug_info.update({"error": "MISSING_RAW_DATA", "phase": "decode_enc"})
            return None

        endpoint = f"/chat/getBase64FromMediaMessage/{self.instance_name}"
        url = f"{settings.EVOLUTION_BASE_URL.rstrip('/')}{endpoint}"
        debug_info["decode_endpoint"] = endpoint
        headers = {"Content-Type": "application/json"}
        if settings.EVOLUTION_API_KEY:
            headers["apikey"] = settings.EVOLUTION_API_KEY

        try:
            response = requests.post(url, headers=headers, json={"message": raw_data}, timeout=40)
            debug_info["http_status"] = response.status_code
            response_preview = (response.text or "").strip().replace("\n", " ")
            if len(response_preview) > 220:
                response_preview = response_preview[:220] + "..."
            if response_preview:
                debug_info["response_preview"] = response_preview
            response.raise_for_status()
            parsed = response.json()
            data = parsed if isinstance(parsed, dict) else {}
            b64_data = str(data.get("base64") or "").strip()
            if not b64_data:
                debug_info.update({"error": "EMPTY_BASE64", "phase": "decode_enc"})
                return None
            if b64_data.startswith("data:") and ";base64," in b64_data:
                b64_data = b64_data.split(";base64,", 1)[1]

            decoded_bytes = base64.b64decode(b64_data)
            file_name = str(data.get("fileName") or "").strip()
            mime_type = str(data.get("mimetype") or "").strip()
            debug_info.update({"phase": "decode_enc", "result": "decoded"})
            return decoded_bytes, file_name, mime_type
        except requests.HTTPError as ex:
            debug_info.update(
                {
                    "error": "DECODE_HTTP_ERROR",
                    "exception_type": type(ex).__name__,
                    "exception": str(ex),
                }
            )
            return None
        except requests.RequestException as ex:
            debug_info.update(
                {
                    "error": "DECODE_REQUEST_FAILED",
                    "exception_type": type(ex).__name__,
                    "exception": str(ex),
                }
            )
            return None
        except Exception as ex:
            debug_info.update(
                {
                    "error": "DECODE_UNKNOWN_ERROR",
                    "exception_type": type(ex).__name__,
                    "exception": str(ex),
                }
            )
            return None

    @staticmethod
    def _guess_media_extension(media_url: str, media_mime_type: str) -> str:
        path_extension = os.path.splitext(urlparse(media_url).path)[1]
        if path_extension:
            return path_extension.lower()

        mime_type = (media_mime_type or "").split(";", 1)[0].strip().lower()
        if mime_type == "audio/ogg":
            return ".ogg"
        if mime_type == "audio/opus":
            return ".opus"
        if mime_type == "audio/mpeg":
            return ".mp3"
        if mime_type == "audio/mp4":
            return ".m4a"

        return ".bin"

    @staticmethod
    def _extract_from_me(row) -> bool:
        key = row.get("key", {}) if isinstance(row.get("key"), dict) else {}
        return bool(key.get("fromMe") or row.get("fromMe") or row.get("from_me"))

    @staticmethod
    def _extract_direction(row) -> str:
        return Message.Direction.OUTBOUND if IngestionService._extract_from_me(row) else Message.Direction.INBOUND

    @staticmethod
    def _extract_sender_wa_id(row) -> str:
        wa_id = str(IngestionService._extract_wa_id(row) or "").strip()
        if not wa_id:
            return ""
        return "me" if IngestionService._extract_from_me(row) else wa_id

    @staticmethod
    def _extract_recipient_wa_id(row) -> str:
        wa_id = str(IngestionService._extract_wa_id(row) or "").strip()
        if not wa_id:
            return ""
        return wa_id if IngestionService._extract_from_me(row) else "me"

    @staticmethod
    def _extract_quoted_external_id(row) -> str:
        message = row.get("message") if isinstance(row.get("message"), dict) else {}
        if not message:
            return ""

        def _context_from(message_key: str):
            payload = message.get(message_key)
            if isinstance(payload, dict):
                context = payload.get("contextInfo")
                if isinstance(context, dict):
                    return context
            return None

        context_candidates = [
            _context_from("extendedTextMessage"),
            _context_from("imageMessage"),
            _context_from("videoMessage"),
            _context_from("audioMessage"),
            _context_from("documentMessage"),
            row.get("contextInfo"),
        ]

        for context in context_candidates:
            if isinstance(context, dict):
                quoted = context.get("stanzaId") or context.get("quotedMessageId") or context.get("quotedMessageKey", {}).get("id")
                if quoted:
                    return str(quoted).strip()
        return ""

    @staticmethod
    def _is_generic_self_label(label: str) -> bool:
        cleaned = str(label or "").strip().lower()
        return cleaned in {"você", "voce", "you", "yo", "me", "eu"}

    @staticmethod
    def _sanitize_contact_name(name: str, from_me: bool) -> str:
        value = str(name or "").strip()
        if not value:
            return ""
        if from_me and IngestionService._is_generic_self_label(value):
            return ""
        if IngestionService._is_name_like_number(value):
            return ""
        return value

    @staticmethod
    def _is_name_like_number(name: str) -> bool:
        cleaned = "".join(ch for ch in str(name or "").strip() if ch.isdigit())
        return len(cleaned) >= 7 and len(cleaned) >= max(1, len(str(name or "").strip()) - 2)

    def _pick_best_contact_name(self, subset_df) -> str:
        if subset_df is None or subset_df.empty:
            return ""

        inbound_subset = subset_df[subset_df["from_me"] == False]
        candidates = []
        if not inbound_subset.empty:
            for _, row in inbound_subset.iterrows():
                candidates.append(
                    self._sanitize_contact_name(
                        str(row.get("name") or "").strip(),
                        bool(row.get("from_me", False)),
                    )
                )

        if not candidates:
            for _, row in subset_df.iterrows():
                candidates.append(
                    self._sanitize_contact_name(
                        str(row.get("name") or "").strip(),
                        bool(row.get("from_me", False)),
                    )
                )

        candidates = [c for c in candidates if c]
        return candidates[-1] if candidates else ""

    def _download_media_files_async(self, df_audio):
        """Descarga audios en background después de completar la ingesta"""
        for row in df_audio.to_dict("records"):
            media_url = str(row.get("media_url") or "").strip()
            media_mime_type = str(row.get("media_mime_type") or "").strip()
            external_id = row.get("external_id")
            raw_data = row.get("raw_data") if isinstance(row.get("raw_data"), dict) else {}
            if media_url and external_id:
                try:
                    media_file_path = self._download_media_file(
                        external_id=external_id,
                        media_url=media_url,
                        media_mime_type=media_mime_type,
                        raw_data=raw_data,
                    )
                    if media_file_path:
                        Message.objects.filter(external_id=external_id).update(media_file=media_file_path)
                except Exception:
                    pass

    @staticmethod
    def _extract_content(row) -> str:
        message = row.get("message") if isinstance(row.get("message"), dict) else {}
        if "conversation" in message:
            return str(message.get("conversation") or "")
        if "extendedTextMessage" in message:
            return str((message.get("extendedTextMessage") or {}).get("text") or "")
        if "imageMessage" in message:
            return str((message.get("imageMessage") or {}).get("caption") or "[image]")
        if "videoMessage" in message:
            return str((message.get("videoMessage") or {}).get("caption") or "[video]")
        if "audioMessage" in message:
            return "[audio]"
        if "documentMessage" in message:
            return str((message.get("documentMessage") or {}).get("fileName") or "[document]")
        return str(row.get("content") or row.get("text") or row.get("body") or "")

    @staticmethod
    def _extract_type(row) -> str:
        raw_type = str(row.get("messageType") or row.get("type") or "other").lower()
        if "text" in raw_type or raw_type == "conversation":
            return Message.MessageType.TEXT
        if "audio" in raw_type:
            return Message.MessageType.AUDIO
        if "image" in raw_type:
            return Message.MessageType.IMAGE
        if "video" in raw_type:
            return Message.MessageType.VIDEO
        if "sticker" in raw_type:
            return Message.MessageType.OTHER
        if "document" in raw_type:
            return Message.MessageType.OTHER
        if "reaction" in raw_type:
            return Message.MessageType.OTHER
        if "location" in raw_type:
            return Message.MessageType.OTHER
        if "contacts" in raw_type:
            return Message.MessageType.OTHER
        return Message.MessageType.OTHER

    @staticmethod
    def _extract_timestamp(row):
        raw = row.get("messageTimestamp") or row.get("timestamp") or row.get("time")
        parsed = None
        if isinstance(raw, str):
            parsed = parse_datetime(raw)
        elif isinstance(raw, (int, float)):
            parsed = datetime.fromtimestamp(raw, tz=dt_timezone.utc)

        if not parsed:
            parsed = timezone.now()

        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone=dt_timezone.utc)
        return parsed

    @staticmethod
    def _notify(progress_callback, percent: int, message: str):
        if callable(progress_callback):
            progress_callback(percent, message)
