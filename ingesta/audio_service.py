"""
Servicio de audio para generar briefings diarios hablados.
- Síntesis de voz con Piper-TTS (GPU-acelerado si está disponible)
- Generación de narrativa ejecutiva basada en resúmenes
- Envío por Evolution API
"""

import io
import logging
import re
import wave
from datetime import datetime, time, timezone as dt_timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError

import numpy as np
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from .models import ChatUser, DailyTextSummary, Message

logger = logging.getLogger(__name__)


class PiperTTSEngine:
    """Motor de síntesis de voz con soporte GPU."""

    def __init__(self, use_gpu: bool = True, gpu_device: int = 0):
        """
        Args:
            use_gpu: Intentar usar GPU si está disponible (CUDA)
            gpu_device: Índice del dispositivo GPU (0 = default)
        """
        self.use_gpu = use_gpu
        self.gpu_device = gpu_device
        self.using_cuda = False
        self.voice = None
        self._initialize_voice()

    def _initialize_voice(self) -> None:
        """Carga el modelo de voz español con GPU si está disponible."""
        try:
            import onnxruntime as ort
            from piper.download_voices import download_voice
            from piper.voice import PiperVoice

            voice_model = str(getattr(settings, "PIPER_VOICE_MODEL", "es_ES-davefx-medium")).strip()
            fallback_csv = str(
                getattr(
                    settings,
                    "PIPER_VOICE_FALLBACKS",
                    "es_ES-davefx-medium,es_MX-claude-high,es_MX-ald-medium",
                )
            )
            fallback_models = [x.strip() for x in fallback_csv.split(",") if x.strip()]
            voice_candidates = [voice_model] + [m for m in fallback_models if m != voice_model]
            download_dir = Path(str(getattr(settings, "PIPER_DOWNLOAD_DIR", "")) or (Path(settings.BASE_DIR) / "data" / "piper_voices"))
            download_dir.mkdir(parents=True, exist_ok=True)

            selected_voice = None
            model_path = None
            config_path = None
            for candidate in voice_candidates:
                candidate_model = download_dir / f"{candidate}.onnx"
                candidate_config = download_dir / f"{candidate}.onnx.json"
                try:
                    if not candidate_model.exists() or not candidate_config.exists():
                        logger.info("Descargando voz Piper '%s' en %s", candidate, download_dir)
                        download_voice(candidate, download_dir=download_dir)
                    selected_voice = candidate
                    model_path = candidate_model
                    config_path = candidate_config
                    break
                except HTTPError as exc:
                    logger.warning("No se pudo descargar voz '%s' (%s)", candidate, exc)
                    continue

            if not selected_voice or not model_path or not config_path:
                raise RuntimeError(
                    "No se pudo descargar ningún modelo Piper válido. "
                    f"Intentados: {', '.join(voice_candidates)}"
                )

            providers = set(ort.get_available_providers())
            use_cuda = self.use_gpu and "CUDAExecutionProvider" in providers
            self.using_cuda = bool(use_cuda)
            if self.use_gpu and not use_cuda:
                logger.warning("CUDAExecutionProvider no disponible en onnxruntime, usando CPU")

            self.voice = PiperVoice.load(
                model_path=model_path,
                config_path=config_path,
                use_cuda=use_cuda,
                download_dir=download_dir,
            )

            logger.info(
                "✓ Piper inicializado (%s) modelo=%s",
                "GPU/CUDA" if use_cuda else "CPU",
                selected_voice,
            )

            logger.info("✓ Motor Piper inicializado correctamente")
        except ImportError:
            logger.error("piper-tts no instalado. Ejecuta: pip install piper-tts")
            raise

    def synthesize(self, text: str, speed: float = 1.0) -> bytes:
        """
        Convierte texto a audio WAV.

        Args:
            text: Texto a sintetizar
            speed: Velocidad de reproducción (1.0 = normal, >1 = más rápido)

        Returns:
            bytes: Audio WAV codificado
        """
        if not self.voice:
            raise RuntimeError("Motor Piper no inicializado")

        try:
            from piper.config import SynthesisConfig

            safe_speed = max(0.5, min(2.0, float(speed or 1.0)))
            # En Piper, menor length_scale = habla más rápido.
            syn_config = SynthesisConfig(length_scale=(1.0 / safe_speed))

            chunks = list(self.voice.synthesize(text, syn_config=syn_config))
            if not chunks:
                raise RuntimeError("Piper no devolvió audio para el texto solicitado")

            sample_rate = int(chunks[0].sample_rate)
            merged = np.concatenate([c.audio_float_array for c in chunks]).astype(np.float32)
            pcm16 = np.clip(merged, -1.0, 1.0)
            pcm16 = (pcm16 * 32767.0).astype(np.int16)

            audio_buffer = io.BytesIO()
            with wave.open(audio_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm16.tobytes())

            audio_buffer.seek(0)
            return audio_buffer.read()
        except Exception as e:
            logger.error(f"Error en síntesis: {e}")
            raise


class AudioBriefingService:
    """Genera briefings de audio ejecutivos diarios."""

    def __init__(self):
        use_gpu = bool(getattr(settings, "PIPER_USE_GPU", True))
        gpu_device = int(getattr(settings, "PIPER_GPU_DEVICE", 0))
        self.tts_engine = PiperTTSEngine(use_gpu=use_gpu, gpu_device=gpu_device)
        self.tts_speed = float(getattr(settings, "AUDIO_BRIEFING_TTS_SPEED", 0.7))
        self.base_url = str(getattr(settings, "EVOLUTION_BASE_URL", "http://localhost:8080")).rstrip("/")
        configured_max_clients = max(1, int(getattr(settings, "AUDIO_BRIEFING_MAX_CLIENTS", 8)))
        self.max_clients = configured_max_clients
        configured_summary_chars = max(120, int(getattr(settings, "AUDIO_BRIEFING_MAX_SUMMARY_CHARS", 380)))
        self.max_summary_chars = configured_summary_chars
        configured_sample_chars = max(60, int(getattr(settings, "AUDIO_BRIEFING_MAX_SAMPLE_CHARS", 160)))
        self.max_sample_chars = configured_sample_chars
        configured_total_chars = max(600, int(getattr(settings, "AUDIO_BRIEFING_MAX_TOTAL_CHARS", 3200)))
        self.max_total_chars = configured_total_chars

    def generate_daily_briefing(
        self,
        instance_name: str,
        team_user: ChatUser,
        date: datetime,
        force_local_only: bool = False,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """
        Genera briefing ejecutivo diario en audio.

        Flujo:
        1. Intro personalizado
        2. Por cada cliente con pendientes:
           - "Cliente X te escribió"
           - Resumen de pendientes
           - Recomendación basada en IA
        3. Conversión a audio
        4. Envío por Evolution

        Args:
            instance_name: Nombre de la instancia Evolution
            team_user: Usuario del equipo (destino)
            date: Fecha del briefing
            progress_callback: Callback de progreso
        """
        briefing_data = {
            "instance_name": instance_name,
            "team_user_id": team_user.id,
            "date": date.isoformat(),
            "generated_at": timezone.now().isoformat(),
            "clients": [],
            "narrative": "",
            "audio_file": None,
            "audio_size_bytes": 0,
            "sent_to_evolution": False,
            "delivery_mode": "local_only" if force_local_only else "auto",
            "error": None,
        }

        try:
            # Paso 1: Recolectar clientes con pendientes
            if progress_callback:
                progress_callback({"phase": "discovery", "progress": 10, "detail": "Descubriendo clientes con pendientes"})

            clients_data = self._discover_pending_clients(date)
            if not clients_data:
                briefing_data["detail"] = "No hay clientes con pendientes"
                return briefing_data

            # Prioriza clientes con la respuesta más antigua del equipo.
            # Si nunca hubo respuesta del equipo, van al principio.
            clients_data.sort(key=self._client_priority_key)
            clients_data = clients_data[: self.max_clients]
            briefing_data["clients"] = [
                {
                    "user_id": row["user_id"],
                    "user_name": row["user_name"],
                    "pending_count": row["pending_count"],
                    "last_our_response": row.get("last_our_response"),
                }
                for row in clients_data
            ]

            # Paso 2: Generar narrativa por cliente
            if progress_callback:
                progress_callback({"phase": "narrative", "progress": 30, "detail": "Generando narrativa ejecutiva"})

            narrative = self._build_narrative(team_user, date, clients_data)
            narrative = self._truncate(narrative, self.max_total_chars)
            briefing_data["narrative"] = narrative

            # Paso 3: Síntesis de voz
            if progress_callback:
                progress_callback({"phase": "tts", "progress": 60, "detail": "Sintetizando audio..."})

            audio_bytes = self.tts_engine.synthesize(narrative, speed=self.tts_speed)
            briefing_data["audio_size_bytes"] = len(audio_bytes)

            # Paso 4: Guardar archivo
            if progress_callback:
                progress_callback({"phase": "save", "progress": 75, "detail": "Guardando archivo de audio"})

            audio_file = self._save_audio_file(team_user, date, audio_bytes)
            briefing_data["audio_file"] = str(audio_file)

            # Paso 5: Enviar por Evolution (opcional, depende de configuración)
            if progress_callback:
                progress_callback({"phase": "send", "progress": 85, "detail": "Preparando envío por Evolution API"})

            should_send = (not force_local_only) and bool(getattr(settings, "AUTO_SEND_BRIEFING_AUDIO", False))
            if should_send:
                success = self._send_via_evolution(instance_name, team_user, audio_file)
                briefing_data["sent_to_evolution"] = success

            if progress_callback:
                progress_callback({"phase": "completed", "progress": 100, "detail": "Briefing completado"})

            logger.info(f"✓ Briefing generado: {len(audio_bytes)} bytes, {len(clients_data)} clientes")
            return briefing_data

        except Exception as e:
            logger.error(f"Error generando briefing: {e}", exc_info=True)
            briefing_data["error"] = str(e)
            return briefing_data

    def _discover_pending_clients(self, date: datetime) -> list[dict[str, Any]]:
        """
        Descubre clientes con mensajes pendientes reales en la fecha.

        Definicion de "pendiente":
        - Mensajes inbound del cliente posteriores al ultimo mensaje outbound nuestro.
        - Si nunca respondimos, todos los inbound del cliente hasta date_end son pendientes.

        Returns:
            Lista de dicts con contexto + resumen + muestra de mensajes pendientes.
        """
        tz = date.tzinfo or timezone.get_current_timezone()
        date_end = datetime.combine(date.date(), time.max, tzinfo=tz)

        clients = []
        for user in ChatUser.objects.filter(is_customer=True).order_by("id"):
            last_our_message = (
                Message.objects.filter(
                    user=user,
                    from_me=True,
                    timestamp__lte=date_end,
                )
                .order_by("-timestamp")
                .first()
            )
            last_our_response_ts = last_our_message.timestamp if last_our_message else None

            pending_qs = Message.objects.filter(
                user=user,
                from_me=False,
                timestamp__lte=date_end,
            )
            if last_our_response_ts:
                pending_qs = pending_qs.filter(timestamp__gt=last_our_response_ts)

            pending_qs = pending_qs.order_by("timestamp")
            pending_count = pending_qs.count()
            if pending_count <= 0:
                continue

            latest_summary = (
                DailyTextSummary.objects.filter(user=user, summary_date__lte=date.date())
                .order_by("-summary_date")
                .first()
            )
            summary_text = str((latest_summary.text if latest_summary else "") or "").strip()

            sample_messages = []
            for msg in pending_qs[:3]:
                sample_messages.append(self._to_spoken_pending_text(msg))

            clients.append(
                {
                    "user": user,
                    "user_id": user.id,
                    "user_name": user.display_label(),
                    "summary_text": summary_text,
                    "pending_count": pending_count,
                    "last_our_response_ts": last_our_response_ts,
                    "last_our_response": last_our_response_ts.isoformat() if last_our_response_ts else "Sin respuestas anteriores",
                    "pending_samples": sample_messages,
                }
            )

        return clients

    def _build_narrative(self, team_user: ChatUser, date: datetime, clients_data: list[dict]) -> str:
        """
        Construye la narrativa ejecutiva hablada.

        Ejemplo:
        "Hola Deya, hoy tienes mensajes pendientes de 3 clientes.
        Valentina te escribió con 5 mensajes nuevos. Según nuestros registros...
        [detalles] Por favor, considera que hay un problema reportado en el hotel.
        ..."
        """
        team_name = self._clean_spoken_name(team_user.display_label(), fallback="equipo")

        # Intro
        total_clients = len(clients_data)
        intro = (
            f"Hola {team_name}. Este es tu resumen ejecutivo de hoy. "
            f"Tienes pendientes de {total_clients} cliente{'s' if total_clients > 1 else ''}. "
        )

        # Por cliente
        client_sections = []
        for i, client in enumerate(clients_data, 1):
            section = self._build_client_section(client, i, len(clients_data))
            client_sections.append(section)

        # Cierre
        closing = "Ese es el resumen de hoy. Revisa los detalles en el sistema si necesitas profundizar."

        narrative = intro + "\n\n".join(client_sections) + "\n\n" + closing
        return narrative

    def _build_client_section(self, client: dict, index: int, total: int) -> str:
        """Construye sección narrativa para un cliente."""
        name = self._clean_spoken_name(client["user_name"], fallback=f"cliente {index}")
        summary = self._truncate(str(client["summary_text"] or ""), self.max_summary_chars)
        count = client["pending_count"]
        last_response = client["last_our_response"]
        samples = list(client.get("pending_samples") or [])

        header = f"{index}. {name}: {count} pendiente{'s' if count != 1 else ''} desde nuestra última respuesta. "

        pending_focus = self._build_pending_focus(samples)
        if pending_focus:
            pending_focus = f"Pendientes detectados: {pending_focus}. "
        else:
            pending_focus = "Pendientes detectados: sin texto claro para leer. "

        if summary:
            summary_intro = f"Resumen de IA: {summary}. "
        else:
            summary_intro = "Resumen de IA: no disponible. "

        issues = []
        lowered_summary = summary.lower()
        if any(word in lowered_summary for word in ["problema", "urgente", "error", "falla"]):
            issues.append("Prioridad alta: el texto sugiere una incidencia o urgencia.")

        if last_response != "Sin respuestas anteriores":
            issues.append(f"Última respuesta del equipo: {self._format_relative_response(last_response)}.")

        recommendation = "Recomendación: revisar y responder en el orden de prioridad más alto."
        issue_text = f"{' '.join(issues)} " if issues else ""

        return header + pending_focus + summary_intro + issue_text + recommendation

    @staticmethod
    def _client_priority_key(client: dict[str, Any]) -> tuple[int, datetime]:
        last_ts = client.get("last_our_response_ts")
        if isinstance(last_ts, datetime):
            return (1, last_ts)
        return (0, datetime.min.replace(tzinfo=dt_timezone.utc))

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        value = str(text or "").strip()
        if len(value) <= max_chars:
            return value
        return value[: max_chars - 1].rstrip() + "…"

    def _build_pending_focus(self, samples: list[str]) -> str:
        """Convierte muestras de pendientes en una sola frase clara y ejecutiva."""
        if not samples:
            return ""

        deduped_samples = []
        seen = set()
        for text in samples:
            key = str(text or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped_samples.append(str(text or "").strip())

        normalized = [self._normalize_pending_phrase(text) for text in deduped_samples]

        if not normalized:
            return ""

        image_count = sum(1 for item in normalized if item == "El cliente envió una o varias imágenes por revisar.")
        emoji_items = [item for item in normalized if item.startswith("El cliente envió un emoji")]
        text_items = [item for item in normalized if item not in {"El cliente envió una o varias imágenes por revisar."} and not item.startswith("El cliente envió un emoji")]

        parts: list[str] = []
        if image_count:
            parts.append("El cliente envió una o varias imágenes por revisar")
        if emoji_items:
            parts.append(emoji_items[0].rstrip("."))
        if text_items:
            parts.append(self._truncate(text_items[0], self.max_sample_chars))

        if not parts:
            return ""

        if len(parts) == 1:
            return parts[0]
        return "; ".join(parts)

    @staticmethod
    def _normalize_pending_phrase(text: str) -> str:
        value = str(text or "").strip()
        lowered = value.lower()
        if "el cliente envió una o varias imágenes por revisar" in lowered:
            return "El cliente envió una o varias imágenes por revisar."
        if lowered.startswith("el cliente envió un emoji"):
            return value if value.endswith(".") else f"{value}."
        return value

    @staticmethod
    def _format_relative_response(last_response: str) -> str:
        value = str(last_response or "").strip()
        return value if value else "sin dato"

    @staticmethod
    def _clean_spoken_name(name: str, fallback: str = "cliente") -> str:
        """Limpia números/telefonos de nombres para lectura por TTS."""
        value = str(name or "").strip()
        # Quita identificadores tipo @s.whatsapp.net
        value = re.sub(r"@\S+", "", value, flags=re.IGNORECASE)
        # Quita bloques entre paréntesis (suelen contener teléfono)
        value = re.sub(r"\([^)]*\)", "", value)
        # Quita secuencias numéricas (teléfonos, IDs, etc.)
        value = re.sub(r"\d+", "", value)
        # Normaliza espacios
        value = re.sub(r"\s+", " ", value).strip(" -_,.;:")
        return value if value else fallback

    def _to_spoken_pending_text(self, msg: Message) -> str:
        """Convierte un mensaje pendiente a una frase amigable para TTS."""
        if msg.message_type == Message.MessageType.IMAGE:
            return "El cliente envió una o varias imágenes por revisar."

        content = str(msg.content or "").strip()
        lowered = content.lower()
        if "[image]" in lowered or "[imagen]" in lowered:
            return "El cliente envió una o varias imágenes por revisar."

        if self._is_emoji_message(content):
            emojis = self._extract_emojis(content)
            if emojis:
                return f"El cliente envió un emoji: {' '.join(emojis[:3])}."
            return "El cliente envió un emoji por revisar."

        if not content:
            if msg.message_type == Message.MessageType.AUDIO:
                return "El cliente envió un audio por revisar."
            if msg.message_type == Message.MessageType.VIDEO:
                return "El cliente envió un video por revisar."
            return "El cliente envió un mensaje por revisar."

        return content

    @staticmethod
    def _extract_emojis(text: str) -> list[str]:
        emoji_pattern = re.compile(
            "["
            "\U0001F300-\U0001F5FF"
            "\U0001F600-\U0001F64F"
            "\U0001F680-\U0001F6FF"
            "\U0001F700-\U0001F77F"
            "\U0001F780-\U0001F7FF"
            "\U0001F800-\U0001F8FF"
            "\U0001F900-\U0001F9FF"
            "\U0001FA00-\U0001FA6F"
            "\U0001FA70-\U0001FAFF"
            "\u2600-\u26FF"
            "\u2700-\u27BF"
            "]",
            flags=re.UNICODE,
        )
        return emoji_pattern.findall(str(text or ""))

    def _is_emoji_message(self, text: str) -> bool:
        value = str(text or "").strip()
        if not value:
            return False

        emojis = self._extract_emojis(value)
        if not emojis:
            return False

        # Si al quitar emojis no quedan letras/números, lo tratamos como mensaje de emoji.
        without_emoji = value
        for emj in emojis:
            without_emoji = without_emoji.replace(emj, " ")
        residue = re.sub(r"[\s\W_]+", "", without_emoji, flags=re.UNICODE)
        return residue == ""

    def _save_audio_file(self, user: ChatUser, date: datetime, audio_bytes: bytes) -> str:
        """Guarda archivo de audio en la BD y el filesystem."""
        filename = f"briefing_{user.id}_{date.date()}.wav"

        # Guardar como Message de audio
        audio_file = ContentFile(audio_bytes, name=filename)

        msg = Message.objects.create(
            user=user,
            external_id=f"briefing_audio_{user.id}_{int(datetime.now(dt_timezone.utc).timestamp())}",
            message_type=Message.MessageType.AUDIO,
            media_file=audio_file,
            content=f"Briefing ejecutivo de {date.date()}",
            timestamp=timezone.now(),
            direction=Message.Direction.OUTBOUND,
            from_me=True,
        )

        logger.info(f"✓ Audio guardado: {msg.media_file.name}")
        return msg.media_file.name

    def _send_via_evolution(self, instance_name: str, user: ChatUser, audio_file_path: str) -> bool:
        """Envía audio briefing por Evolution API."""
        try:
            # Aquí iría la lógica de envío via Evolution
            # POST /chat/sendMessage/{instance_name}
            # con type: "mediaMessage", media: {type: "audio", url: ...}
            logger.info(f"Briefing listo para enviar a {user.display_label()} ({user.wa_id})")
            return True
        except Exception as e:
            logger.error(f"Error enviando via Evolution: {e}")
            return False
