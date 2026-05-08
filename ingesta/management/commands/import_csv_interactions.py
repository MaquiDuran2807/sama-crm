import csv
import re
from datetime import datetime, timezone as dt_timezone
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ingesta.models import ChatUser, UserInteraction


class Command(BaseCommand):
    help = "Importa interacciones desde CSV y las registra como interacciones del usuario."

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True, help="Ruta al archivo CSV")
        parser.add_argument("--delimiter", default=",", help="Separador CSV (default: ,)")
        parser.add_argument("--encoding", default="utf-8", help="Encoding CSV (default: utf-8)")
        parser.add_argument("--source", default="csv_calls", help="Etiqueta source para rastreo")
        parser.add_argument("--dry-run", action="store_true", help="No persiste cambios")

    def handle(self, *args, **options):
        csv_path = Path(str(options["csv"]))
        if not csv_path.exists():
            raise CommandError(f"No existe el CSV: {csv_path}")

        delimiter = str(options["delimiter"] or ",")
        encoding = str(options["encoding"] or "utf-8")
        source = str(options["source"] or "csv_calls").strip() or "csv_calls"
        dry_run = bool(options["dry_run"])

        created = 0
        skipped = 0
        errors = 0

        with csv_path.open("r", encoding=encoding, newline="") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            if not reader.fieldnames:
                raise CommandError("El CSV no tiene encabezados")

            for idx, row in enumerate(reader, start=2):
                try:
                    user = self._resolve_user(row)
                    if not user:
                        skipped += 1
                        self.stdout.write(self.style.WARNING(f"[fila {idx}] Usuario no encontrado, se omite"))
                        continue

                    occurred_at = self._parse_ts(self._pick(row, ["timestamp", "occurred_at", "datetime", "date", "ts"]))
                    duration_seconds = self._parse_int(self._pick(row, ["duration_seconds", "callDuration", "duration", "seconds"]))
                    is_video = self._parse_bool(self._pick(row, ["is_video", "video", "isVideo"]))
                    source_ref = str(self._pick(row, ["source_ref", "external_id", "id", "call_id"]) or "").strip()
                    content = str(self._pick(row, ["content", "note", "notes", "detail"]) or "").strip()
                    interaction_type = str(self._pick(row, ["interaction_type", "type"]) or "call").strip().lower()
                    if interaction_type not in {"call", "note", "other"}:
                        interaction_type = "call"

                    direction_raw = str(self._pick(row, ["direction"]) or "outbound").strip().lower()
                    direction = "inbound" if direction_raw == "inbound" else "outbound"
                    from_me = self._parse_bool(self._pick(row, ["from_me", "ours", "is_ours"]))
                    if from_me is None:
                        from_me = True

                    dedupe_qs = UserInteraction.objects.filter(
                        user=user,
                        interaction_type=interaction_type,
                        occurred_at=occurred_at,
                        source=source,
                        source_ref=source_ref,
                    )
                    if source_ref and dedupe_qs.exists():
                        skipped += 1
                        continue

                    payload = {
                        "user": user,
                        "interaction_type": interaction_type,
                        "from_me": from_me,
                        "direction": direction,
                        "occurred_at": occurred_at,
                        "duration_seconds": duration_seconds,
                        "is_video": bool(is_video),
                        "source": source,
                        "source_ref": source_ref,
                        "content": content,
                        "raw_data": row,
                    }

                    if dry_run:
                        created += 1
                        continue

                    with transaction.atomic():
                        UserInteraction.objects.create(**payload)
                        if occurred_at and (not user.last_interaction or occurred_at > user.last_interaction):
                            user.last_interaction = occurred_at
                            user.save(update_fields=["last_interaction"])

                    created += 1
                except Exception as ex:
                    errors += 1
                    self.stdout.write(self.style.ERROR(f"[fila {idx}] Error: {ex}"))

        mode = "DRY RUN" if dry_run else "IMPORT"
        self.stdout.write(self.style.SUCCESS(f"{mode} completado: creados={created}, omitidos={skipped}, errores={errors}"))

    def _pick(self, row: dict, keys: list[str]):
        lower_map = {str(k).strip().lower(): v for k, v in (row or {}).items()}
        for key in keys:
            val = lower_map.get(key.lower())
            if val is not None and str(val).strip() != "":
                return val
        return None

    def _resolve_user(self, row: dict) -> ChatUser | None:
        user_id = self._pick(row, ["user_id", "chat_user_id"])
        if user_id:
            try:
                return ChatUser.objects.filter(id=int(str(user_id).strip())).first()
            except ValueError:
                pass

        wa_id = str(self._pick(row, ["wa_id", "jid", "remote_jid"]) or "").strip()
        if wa_id:
            if "@" not in wa_id and wa_id:
                candidate = f"{wa_id}@s.whatsapp.net"
                user = ChatUser.objects.filter(wa_id=candidate).first() or ChatUser.objects.filter(wa_id=wa_id).first()
            else:
                user = ChatUser.objects.filter(wa_id=wa_id).first()
            if user:
                return user

        phone = str(self._pick(row, ["phone_number", "phone", "number", "recipient"]) or "").strip()
        digits = re.sub(r"\D+", "", phone)
        if digits:
            return (
                ChatUser.objects.filter(phone_number=digits).first()
                or ChatUser.objects.filter(wa_id__startswith=digits).first()
            )

        return None

    def _parse_ts(self, raw):
        if raw is None:
            return timezone.now()

        value = str(raw).strip()
        if value == "":
            return timezone.now()

        if value.isdigit():
            ts_num = int(value)
            if ts_num > 10_000_000_000:
                ts_num = ts_num / 1000
            parsed = datetime.fromtimestamp(ts_num, tz=dt_timezone.utc)
            return parsed

        parsed = parse_datetime(value)
        if parsed is None:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    parsed = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue

        if parsed is None:
            return timezone.now()

        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone=dt_timezone.utc)
        return parsed

    def _parse_int(self, raw):
        if raw is None:
            return None
        txt = str(raw).strip()
        if txt == "":
            return None
        try:
            return max(0, int(float(txt)))
        except ValueError:
            return None

    def _parse_bool(self, raw):
        if raw is None:
            return None
        txt = str(raw).strip().lower()
        if txt in {"1", "true", "t", "yes", "y", "si", "sí"}:
            return True
        if txt in {"0", "false", "f", "no", "n"}:
            return False
        return None
