import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Callable

import requests
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Max, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import (ChatUser, DailyTextSummary, Message, MonthlyTextSummary,
                     SummaryExecutionControl)


@dataclass
class SummaryResult:
    text: str
    has_data: bool
    pending_items: list[str]
    mentioned_people: list[dict[str, str]]
    deadlines: list[dict[str, str]]
    payment_promises: list[dict[str, str]]
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    raw: dict[str, Any]


class TextSummaryService:
    """Genera resumen diario y resumen general mensual solo para mensajes de texto."""

    def __init__(self):
        self.base_url = str(getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = str(getattr(settings, "OLLAMA_MODEL", "llama3.2")).strip() or "llama3.2"
        self.timeout = int(getattr(settings, "AI_SUMMARY_TIMEOUT_SECONDS", 90))

    def run_for_slot(
        self,
        slot_start: datetime,
        slot_end: datetime,
        run_key: str,
        force: bool = False,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        user_ids: list[int] | None = None,
    ) -> SummaryExecutionControl:
        exec_log, _ = SummaryExecutionControl.objects.get_or_create(
            run_key=run_key,
            defaults={
                "slot_start": slot_start,
                "slot_end": slot_end,
                "status": SummaryExecutionControl.Status.RUNNING,
            },
        )

        if exec_log.status == SummaryExecutionControl.Status.COMPLETED and not force:
            return exec_log

        exec_log.slot_start = slot_start
        exec_log.slot_end = slot_end
        exec_log.status = SummaryExecutionControl.Status.RUNNING
        exec_log.finished_at = None
        exec_log.detail = ""
        exec_log.save(update_fields=["slot_start", "slot_end", "status", "finished_at", "detail"])

        inbound_q = Q(timestamp__gte=slot_start, timestamp__lt=slot_end, message_type=Message.MessageType.TEXT)
        users_qs = (
            ChatUser.objects.filter(is_customer=True, messages__in=Message.objects.filter(inbound_q))
            .distinct()
            .order_by("id")
        )
        if user_ids:
            users_qs = users_qs.filter(id__in=user_ids)
        users = list(users_qs)
        exec_log.eligible_users = len(users)
        exec_log.save(update_fields=["eligible_users"])

        if progress_callback:
            progress_callback(
                {
                    "phase": "discover_users",
                    "eligible_users": len(users),
                    "processed_users": 0,
                    "failed_users": 0,
                    "skipped_users": 0,
                    "status": exec_log.status,
                }
            )

        if not users:
            exec_log.status = SummaryExecutionControl.Status.SKIPPED
            exec_log.detail = "Sin usuarios con mensajes de texto en la ventana."
            exec_log.finished_at = timezone.now()
            exec_log.save(update_fields=["status", "detail", "finished_at"])
            return exec_log

        counters = defaultdict(int)
        errors = []

        for user_index, user in enumerate(users, start=1):
            try:
                def on_user_day_progress(day_done: int, day_total: int) -> None:
                    if not progress_callback:
                        return
                    progress_callback(
                        {
                            "phase": "processing_days",
                            "eligible_users": len(users),
                            "processed_users": counters["processed_users"],
                            "failed_users": counters["failed_users"],
                            "skipped_users": counters["skipped_users"],
                            "current_user_index": user_index,
                            "current_user_total_days": day_total,
                            "current_user_day_done": day_done,
                            "status": exec_log.status,
                        }
                    )

                processed = self._process_user_window(
                    user=user,
                    slot_start=slot_start,
                    slot_end=slot_end,
                    exec_log=exec_log,
                    user_progress_callback=on_user_day_progress,
                    force=force,
                )
                if processed:
                    counters["processed_users"] += 1
                else:
                    counters["skipped_users"] += 1
            except Exception as exc:
                counters["failed_users"] += 1
                errors.append(f"user_id={user.id}: {exc}")

            exec_log.processed_users = counters["processed_users"]
            exec_log.skipped_users = counters["skipped_users"]
            exec_log.failed_users = counters["failed_users"]
            exec_log.save(update_fields=["processed_users", "skipped_users", "failed_users"])

            if progress_callback:
                progress_callback(
                    {
                        "phase": "processing_users",
                        "eligible_users": len(users),
                        "processed_users": counters["processed_users"],
                        "failed_users": counters["failed_users"],
                        "skipped_users": counters["skipped_users"],
                        "status": exec_log.status,
                    }
                )

        if errors:
            exec_log.status = SummaryExecutionControl.Status.FAILED
            exec_log.detail = " | ".join(errors[:20])
        else:
            exec_log.status = SummaryExecutionControl.Status.COMPLETED
            exec_log.detail = "Procesamiento finalizado"
        exec_log.finished_at = timezone.now()
        exec_log.save(update_fields=["status", "detail", "finished_at"])

        if progress_callback:
            progress_callback(
                {
                    "phase": "finished",
                    "eligible_users": len(users),
                    "processed_users": counters["processed_users"],
                    "failed_users": counters["failed_users"],
                    "skipped_users": counters["skipped_users"],
                    "status": exec_log.status,
                }
            )
        return exec_log

    def compute_accumulation_window(
        self,
        slot_end: datetime,
        fallback_lookback_hours: int = 12,
    ) -> tuple[datetime, dict[str, Any]]:
        """Retorna ventana acumulativa: pendientes historicos + hoy.

        Regla de negocio:
        - Siempre incluir hoy para actualizar el reporte actual.
        - Si existen dias pendientes (sin resumen o con cambios), expandir hacia atras
          hasta el dia pendiente mas antiguo.
        - Si no hay pendientes, usar hoy; si hoy no tiene mensajes, usar fallback lookback.
        """
        tz = slot_end.tzinfo or timezone.get_current_timezone()
        today_start = datetime.combine(slot_end.date(), datetime.min.time(), tzinfo=tz)

        # Regla solicitada: cada ejecucion avanza 24h mas hacia atras desde el ultimo tramo acumulado.
        step_back_hours = 24
        last_accumulated_run = None
        recent_completed = SummaryExecutionControl.objects.filter(
            status=SummaryExecutionControl.Status.COMPLETED
        ).order_by("-started_at")[:200]
        for item in recent_completed:
            if isinstance(item.meta, dict) and item.meta.get("accumulation_cursor_start"):
                last_accumulated_run = item
                break

        oldest_message_ts = (
            Message.objects.filter(message_type=Message.MessageType.TEXT, user__is_customer=True)
            .order_by("timestamp")
            .values_list("timestamp", flat=True)
            .first()
        )

        cursor_start: datetime | None = None
        if last_accumulated_run and isinstance(last_accumulated_run.meta, dict):
            raw_cursor = last_accumulated_run.meta.get("accumulation_cursor_start")
            if raw_cursor:
                try:
                    cursor_start = datetime.fromisoformat(str(raw_cursor))
                    if cursor_start.tzinfo is None:
                        cursor_start = cursor_start.replace(tzinfo=tz)
                except ValueError:
                    cursor_start = None

        if cursor_start is None:
            # Primera corrida acumulada: hoy + ayer (24h hacia atras).
            proposed_start = max(today_start - timedelta(hours=step_back_hours), slot_end - timedelta(hours=max(1, int(fallback_lookback_hours))))
            mode = "accumulation_step_back_init"
        else:
            proposed_start = cursor_start - timedelta(hours=step_back_hours)
            mode = "accumulation_step_back_24h"

        if oldest_message_ts is not None:
            min_start = datetime.combine(oldest_message_ts.date(), datetime.min.time(), tzinfo=tz)
            slot_start = max(min_start, proposed_start)
            reached_oldest = slot_start <= min_start
        else:
            slot_start = proposed_start
            reached_oldest = True

        has_today_text = Message.objects.filter(
            message_type=Message.MessageType.TEXT,
            user__is_customer=True,
            timestamp__gte=today_start,
            timestamp__lt=slot_end,
        ).exists()

        meta = {
            "mode": mode,
            "today_start": today_start.isoformat(),
            "oldest_pending_day": None,
            "has_today_text": has_today_text,
            "accumulation_step_hours": step_back_hours,
            "accumulation_cursor_start": slot_start.isoformat(),
            "accumulation_reached_oldest": reached_oldest,
            "oldest_message_day": oldest_message_ts.date().isoformat() if oldest_message_ts else None,
        }
        return slot_start, meta

    def _find_oldest_pending_day(self, slot_end: datetime) -> date | None:
        """Busca el dia pendiente mas antiguo comparando origen vs resumen persistido."""
        aggregates = list(
            Message.objects.filter(
                message_type=Message.MessageType.TEXT,
                user__is_customer=True,
                timestamp__lt=slot_end,
            )
            .annotate(summary_day=TruncDate("timestamp"))
            .values("user_id", "summary_day")
            .annotate(source_count=Count("id"), source_last_ts=Max("timestamp"))
            .order_by("summary_day")
        )

        if not aggregates:
            return None

        existing_map = {
            (row["user_id"], row["summary_date"]): (row["source_message_count"], row["source_last_message_ts"])
            for row in DailyTextSummary.objects.values(
                "user_id",
                "summary_date",
                "source_message_count",
                "source_last_message_ts",
            )
        }

        oldest_pending: date | None = None
        for row in aggregates:
            key = (row["user_id"], row["summary_day"])
            expected_count = int(row["source_count"] or 0)
            expected_last_ts = row["source_last_ts"]
            current = existing_map.get(key)

            if current is None:
                if oldest_pending is None or row["summary_day"] < oldest_pending:
                    oldest_pending = row["summary_day"]
                continue

            current_count, current_last_ts = current
            if current_count != expected_count or current_last_ts != expected_last_ts:
                if oldest_pending is None or row["summary_day"] < oldest_pending:
                    oldest_pending = row["summary_day"]

        return oldest_pending

    def _process_user_window(
        self,
        user: ChatUser,
        slot_start: datetime,
        slot_end: datetime,
        exec_log: SummaryExecutionControl,
        user_progress_callback: Callable[[int, int], None] | None = None,
        force: bool = False,
    ) -> bool:
        text_qs = Message.objects.filter(
            user=user,
            timestamp__gte=slot_start,
            timestamp__lt=slot_end,
            message_type=Message.MessageType.TEXT,
        ).order_by("timestamp")
        messages = list(text_qs)
        if not messages:
            return False

        by_day: dict[date, list[Message]] = defaultdict(list)
        for msg in messages:
            by_day[msg.timestamp.date()].append(msg)

        processed_any = False
        delta_counters = defaultdict(int)

        ordered_days = sorted(by_day.items(), key=lambda item: item[0])
        total_days = len(ordered_days)

        for day_index, (day, day_messages) in enumerate(ordered_days, start=1):
            day_messages = sorted(day_messages, key=lambda m: m.timestamp)
            source_count = len(day_messages)
            source_last_ts = day_messages[-1].timestamp
            day_end = datetime.combine(day + timedelta(days=1), datetime.min.time(), tzinfo=slot_start.tzinfo or slot_end.tzinfo)
            response_cutoff = min(day_end, slot_end)
            last_team_response_ts = (
                Message.objects.filter(
                    user=user,
                    timestamp__gte=slot_start,
                    timestamp__lt=response_cutoff,
                    from_me=True,
                )
                .order_by("-timestamp")
                .values_list("timestamp", flat=True)
                .first()
            )
            existing = DailyTextSummary.objects.filter(user=user, summary_date=day).first()

            if (
                existing
                and not force
                and existing.source_message_count == source_count
                and existing.source_last_message_ts == source_last_ts
            ):
                if user_progress_callback:
                    user_progress_callback(day_index, total_days)
                continue

            transcript, unresolved = self._build_compact_transcript(day_messages)
            result = self._summarize_day(
                user=user,
                target_day=day,
                compact_transcript=transcript,
                unresolved_count=unresolved,
                last_team_response_ts=last_team_response_ts,
            )

            with transaction.atomic():
                created = False
                if not existing:
                    existing = DailyTextSummary(user=user, summary_date=day)
                    created = True

                existing.text = result.text
                existing.has_data = result.has_data
                existing.pending_items = result.pending_items
                existing.mentioned_people = result.mentioned_people
                existing.deadlines = result.deadlines
                existing.payment_promises = result.payment_promises
                existing.source_message_count = source_count
                existing.source_last_message_ts = source_last_ts
                existing.prompt_tokens = result.prompt_tokens
                existing.completion_tokens = result.completion_tokens
                existing.total_tokens = result.total_tokens
                existing.last_execution = exec_log
                if created:
                    existing.save()
                    delta_counters["daily_created"] += 1
                else:
                    existing.save(
                        update_fields=[
                            "text",
                            "has_data",
                            "pending_items",
                            "mentioned_people",
                            "deadlines",
                            "payment_promises",
                            "source_message_count",
                            "source_last_message_ts",
                            "prompt_tokens",
                            "completion_tokens",
                            "total_tokens",
                            "last_execution",
                            "updated_at",
                        ]
                    )
                    delta_counters["daily_updated"] += 1

            delta_counters["processed_text_messages"] += source_count
            delta_counters["prompt_tokens"] += result.prompt_tokens
            delta_counters["completion_tokens"] += result.completion_tokens
            delta_counters["total_tokens"] += result.total_tokens
            processed_any = True

            if user_progress_callback:
                user_progress_callback(day_index, total_days)

        if not processed_any:
            return False

        touched_months = sorted({(m.timestamp.year, m.timestamp.month) for m in messages})
        for year, month in touched_months:
            month_start = date(year, month, 1)
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            self._refresh_monthly_summary(
                user=user,
                month_start=month_start,
                month_end=month_end,
                exec_log=exec_log,
                delta_counters=delta_counters,
            )

        exec_log.processed_text_messages += delta_counters["processed_text_messages"]
        exec_log.daily_summaries_created += delta_counters["daily_created"]
        exec_log.daily_summaries_updated += delta_counters["daily_updated"]
        exec_log.monthly_summaries_created += delta_counters["monthly_created"]
        exec_log.monthly_summaries_updated += delta_counters["monthly_updated"]
        exec_log.prompt_tokens += delta_counters["prompt_tokens"]
        exec_log.completion_tokens += delta_counters["completion_tokens"]
        exec_log.total_tokens += delta_counters["total_tokens"]
        exec_log.save(
            update_fields=[
                "processed_text_messages",
                "daily_summaries_created",
                "daily_summaries_updated",
                "monthly_summaries_created",
                "monthly_summaries_updated",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
            ]
        )
        return True

    def _refresh_monthly_summary(
        self,
        user: ChatUser,
        month_start: date,
        month_end: date,
        exec_log: SummaryExecutionControl,
        delta_counters: defaultdict,
        force: bool = False,
    ) -> None:
        daily_rows = list(
            DailyTextSummary.objects.filter(
                user=user,
                summary_date__gte=month_start,
                summary_date__lt=month_end,
            ).order_by("summary_date")
        )

        if not daily_rows:
            return

        source_count = sum(int(row.source_message_count or 0) for row in daily_rows)
        source_last_ts_candidates = [row.source_last_message_ts for row in daily_rows if row.source_last_message_ts]
        source_last_ts = max(source_last_ts_candidates) if source_last_ts_candidates else None
        current = (
            MonthlyTextSummary.objects.filter(
                user=user,
                year=month_start.year,
                month=month_start.month,
                is_current=True,
            )
            .order_by("-revision")
            .first()
        )

        if (
            current
            and not force
            and current.source_message_count == source_count
            and current.source_last_message_ts == source_last_ts
        ):
            return

        transcript, unresolved = self._build_monthly_digest_from_daily(daily_rows)
        result = self._summarize_month(
            user=user,
            month_start=month_start,
            compact_transcript=transcript,
            unresolved_count=unresolved,
        )

        with transaction.atomic():
            if current:
                current.is_current = False
                current.save(update_fields=["is_current", "updated_at"])
                revision = current.revision + 1
            else:
                revision = 1

            new_summary = MonthlyTextSummary.objects.create(
                user=user,
                year=month_start.year,
                month=month_start.month,
                text=result.text,
                has_data=result.has_data,
                pending_items=result.pending_items,
                mentioned_people=result.mentioned_people,
                deadlines=result.deadlines,
                payment_promises=result.payment_promises,
                source_message_count=source_count,
                source_last_message_ts=source_last_ts,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                total_tokens=result.total_tokens,
                revision=revision,
                is_current=True,
                last_execution=exec_log,
            )
            _ = new_summary

        if revision == 1:
            delta_counters["monthly_created"] += 1
        else:
            delta_counters["monthly_updated"] += 1

        delta_counters["prompt_tokens"] += result.prompt_tokens
        delta_counters["completion_tokens"] += result.completion_tokens
        delta_counters["total_tokens"] += result.total_tokens

    def rebuild_monthly_summaries_from_daily(
        self,
        run_key: str,
        force: bool = True,
        user_id: int | None = None,
        year: int | None = None,
        month: int | None = None,
    ) -> SummaryExecutionControl:
        now = timezone.now()
        exec_log, _ = SummaryExecutionControl.objects.get_or_create(
            run_key=run_key,
            defaults={
                "slot_start": now,
                "slot_end": now,
                "status": SummaryExecutionControl.Status.RUNNING,
                "detail": "Rebuild mensual desde resúmenes diarios",
            },
        )

        exec_log.status = SummaryExecutionControl.Status.RUNNING
        exec_log.finished_at = None
        exec_log.detail = "Rebuild mensual desde resúmenes diarios"
        exec_log.save(update_fields=["status", "finished_at", "detail"])

        daily_qs = DailyTextSummary.objects.filter(user__is_customer=True)
        if user_id:
            daily_qs = daily_qs.filter(user_id=user_id)
        if year:
            daily_qs = daily_qs.filter(summary_date__year=year)
        if month:
            daily_qs = daily_qs.filter(summary_date__month=month)

        month_pairs = list(
            daily_qs.values_list("user_id", "summary_date__year", "summary_date__month")
            .distinct()
            .order_by("user_id", "summary_date__year", "summary_date__month")
        )

        exec_log.eligible_users = len({p[0] for p in month_pairs})
        exec_log.save(update_fields=["eligible_users"])

        delta_counters = defaultdict(int)
        touched_users: set[int] = set()
        errors: list[str] = []

        for user_pk, y, m in month_pairs:
            try:
                user = ChatUser.objects.get(pk=user_pk, is_customer=True)
                month_start = date(y, m, 1)
                month_end = (month_start + timedelta(days=32)).replace(day=1)

                before_created = delta_counters["monthly_created"]
                before_updated = delta_counters["monthly_updated"]

                self._refresh_monthly_summary(
                    user=user,
                    month_start=month_start,
                    month_end=month_end,
                    exec_log=exec_log,
                    delta_counters=delta_counters,
                    force=force,
                )

                if delta_counters["monthly_created"] > before_created or delta_counters["monthly_updated"] > before_updated:
                    touched_users.add(user_pk)
            except Exception as exc:
                errors.append(f"user_id={user_pk} {y}-{m:02d}: {exc}")

        exec_log.processed_users = len(touched_users)
        exec_log.failed_users = len(errors)
        exec_log.monthly_summaries_created += delta_counters["monthly_created"]
        exec_log.monthly_summaries_updated += delta_counters["monthly_updated"]
        exec_log.prompt_tokens += delta_counters["prompt_tokens"]
        exec_log.completion_tokens += delta_counters["completion_tokens"]
        exec_log.total_tokens += delta_counters["total_tokens"]

        if errors:
            exec_log.status = SummaryExecutionControl.Status.FAILED
            exec_log.detail = " | ".join(errors[:20])
        else:
            exec_log.status = SummaryExecutionControl.Status.COMPLETED
            exec_log.detail = "Rebuild mensual completado"

        exec_log.finished_at = timezone.now()
        exec_log.save(
            update_fields=[
                "processed_users",
                "failed_users",
                "monthly_summaries_created",
                "monthly_summaries_updated",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "status",
                "detail",
                "finished_at",
            ]
        )
        return exec_log

    def _build_monthly_digest_from_daily(self, daily_rows: list[DailyTextSummary]) -> tuple[str, int]:
        lines: list[str] = []
        unresolved = 0
        for row in daily_rows:
            day = row.summary_date.isoformat()
            text = (row.text or "").strip() or "NO_DATA"
            if text.upper() in {"NO_DATA", "NO DATA", "NO-DATA", "NO_DATA."}:
                text = "NO_DATA"
            pending = ", ".join([str(x).strip() for x in (row.pending_items or []) if str(x).strip()]) or "NO_DATA"
            if pending.lower() in {"item", "no_data", "no data", "none", "null", "n/a"}:
                pending = "NO_DATA"

            people = []
            for person in row.mentioned_people or []:
                nombre = str((person or {}).get("nombre") or "NO_DATA").strip() or "NO_DATA"
                motivo = str((person or {}).get("motivo") or "NO_DATA").strip() or "NO_DATA"
                people.append(f"{nombre} ({motivo})")
            people_txt = ", ".join(people) if people else "NO_DATA"

            deadlines = []
            for dl in row.deadlines or []:
                fecha = str((dl or {}).get("fecha") or "NO_DATA").strip() or "NO_DATA"
                detalle = str((dl or {}).get("detalle") or "NO_DATA").strip() or "NO_DATA"
                deadlines.append(f"{fecha}: {detalle}")
            deadlines_txt = ", ".join(deadlines) if deadlines else "NO_DATA"

            payments = []
            for pp in row.payment_promises or []:
                valor = str((pp or {}).get("valor") or "NO_DATA").strip() or "NO_DATA"
                fecha = str((pp or {}).get("fecha") or "NO_DATA").strip() or "NO_DATA"
                detalle = str((pp or {}).get("detalle") or "NO_DATA").strip() or "NO_DATA"
                payments.append(f"{valor} en {fecha} ({detalle})")
            payments_txt = ", ".join(payments) if payments else "NO_DATA"

            if "no respond" in text.lower() or "pendiente" in text.lower():
                unresolved += 1

            lines.append(
                f"{day} | resumen_dia: {text} | pendientes: {pending} | personas: {people_txt} | fechas: {deadlines_txt} | pagos: {payments_txt}"
            )

        if not lines:
            return "NO_DATA", unresolved
        return "\n".join(lines), unresolved

    def _build_compact_transcript(self, messages: list[Message]) -> tuple[str, int]:
        lines = []
        for msg in messages:
            role = "ASESOR" if msg.from_me else "CLIENTE"
            is_media = msg.message_type in {
                Message.MessageType.AUDIO,
                Message.MessageType.IMAGE,
                Message.MessageType.VIDEO,
            }
            content = (msg.content or "").strip()
            if is_media:
                media_label = {
                    Message.MessageType.AUDIO: "[AUDIO]",
                    Message.MessageType.IMAGE: "[IMAGEN]",
                    Message.MessageType.VIDEO: "[VIDEO]",
                }.get(msg.message_type, "[MEDIA]")
                if content:
                    content = f"{media_label} {content}"
                else:
                    content = media_label

            if not content:
                continue

            lines.append(f"{msg.timestamp.strftime('%Y-%m-%d %H:%M')} | {role}: {content}")

        unresolved = 0
        waiting = False
        for msg in messages:
            if (msg.content or "").strip() == "":
                continue
            if msg.from_me:
                waiting = False
            else:
                if waiting:
                    unresolved += 1
                waiting = True

        if waiting:
            unresolved += 1

        if not lines:
            return "NO_DATA", unresolved
        return "\n".join(lines), unresolved

    def _summarize_day(
        self,
        user: ChatUser,
        target_day: date,
        compact_transcript: str,
        unresolved_count: int,
        last_team_response_ts: datetime | None = None,
    ) -> SummaryResult:
        if compact_transcript == "NO_DATA":
            return self._empty_result("NO_DATA")

        if "| ASESOR:" not in compact_transcript and "| CLIENTE:" in compact_transcript:
            fallback_text, fallback_pending = self._build_day_fallback_from_transcript(
                compact_transcript,
                unresolved_count,
                last_team_response_ts=last_team_response_ts,
            )
            if fallback_text != "NO_DATA":
                return SummaryResult(
                    text=fallback_text,
                    has_data=True,
                    pending_items=fallback_pending,
                    mentioned_people=[],
                    deadlines=[],
                    payment_promises=[],
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    raw={"mode": "fallback_no_team_messages"},
                )

        prompt = self._build_day_prompt(user=user, target_day=target_day, transcript=compact_transcript, unresolved_count=unresolved_count)
        result = self._call_model(prompt, summary_kind="day", source_context=compact_transcript)
        if result.has_data:
            return result

        fallback_text, fallback_pending = self._build_day_fallback_from_transcript(
            compact_transcript,
            unresolved_count,
            last_team_response_ts=last_team_response_ts,
        )
        if fallback_text == "NO_DATA":
            return result

        return SummaryResult(
            text=fallback_text,
            has_data=True,
            pending_items=fallback_pending,
            mentioned_people=result.mentioned_people,
            deadlines=result.deadlines,
            payment_promises=result.payment_promises,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            raw=result.raw,
        )

    def _format_spanish_date(self, value: date | datetime | None) -> str:
        if value is None:
            return "NO_DATA"
        if isinstance(value, datetime):
            value = value.date()
        months = [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]
        return f"{value.day} de {months[value.month - 1]} de {value.year}"

    def _build_day_fallback_from_transcript(
        self,
        transcript: str,
        unresolved_count: int,
        last_team_response_ts: datetime | None = None,
    ) -> tuple[str, list[str]]:
        lines = [ln.strip() for ln in str(transcript or "").splitlines() if ln.strip()]
        if not lines:
            return "NO_DATA", []

        client_msgs: list[str] = []
        team_msgs: list[str] = []
        team_audio = 0
        client_audio = 0
        for line in lines:
            if "| CLIENTE:" in line:
                msg = line.split("| CLIENTE:", 1)[1].strip()
                if msg:
                    client_msgs.append(msg)
                    if "[AUDIO]" in msg.upper():
                        client_audio += 1
            elif "| ASESOR:" in line:
                msg = line.split("| ASESOR:", 1)[1].strip()
                if msg:
                    team_msgs.append(msg)
                    if "[AUDIO]" in msg.upper():
                        team_audio += 1

        if not client_msgs and not team_msgs:
            return "NO_DATA", []

        tema = client_msgs[-1] if client_msgs else (team_msgs[-1] if team_msgs else "NO_DATA")
        tema_short = (tema[:140] + "...") if len(tema) > 140 else tema
        if len(team_msgs) == 0:
            if last_team_response_ts is not None:
                estado = f"no hay respuesta nuestra desde el {self._format_spanish_date(last_team_response_ts)}"
            else:
                estado = "no hay respuesta nuestra en el periodo analizado"
        elif team_audio > 0:
            estado = f"con respuesta por audio del equipo ({team_audio})"
        else:
            estado = "con respuesta del equipo"
        text = (
            f"Cliente envió {len(client_msgs)} mensajes y equipo {len(team_msgs)}" + (f" ({team_audio} audios)" if team_audio else "") + ". "
            f"Tema principal: {tema_short}. Estado: {estado}."
        )

        pending: list[str] = []
        if unresolved_count > 0:
            if tema_short and tema_short != "NO_DATA":
                pending.append(f"Responder o confirmar con el cliente sobre: {tema_short}")
            else:
                pending.append("Responder al cliente y confirmar siguiente paso")

        return text, pending

    def _summarize_month(self, user: ChatUser, month_start: date, compact_transcript: str, unresolved_count: int) -> SummaryResult:
        if compact_transcript == "NO_DATA":
            return self._empty_result("NO_DATA")

        prompt = self._build_month_prompt(user=user, month_start=month_start, transcript=compact_transcript, unresolved_count=unresolved_count)
        return self._call_model(prompt, summary_kind="month", source_context=compact_transcript)

    def _build_day_prompt(self, user: ChatUser, target_day: date, transcript: str, unresolved_count: int) -> str:
        return (
            "Eres un analista CRM comercial riguroso. Resume SOLO con evidencia literal del transcript. "
            "Si falta un dato, usa 'NO_DATA'. No inventes ni asumas. Salida SOLO JSON valido sin markdown. "
            "Maximo 150 palabras y minimo 50 a menos que sea 'NO_DATA' en 'resumen_corto', priorizando cambios, insistencias y estado actual.\n"
            f"usuario: {user.display_label()}\n"
            f"fecha_objetivo: {target_day.isoformat()}\n"
            f"mensajes_no_respondidos_detectados: {unresolved_count}\n"
            "schema={"
            "\"resumen_corto\":\"texto corto y puntual\","
            "\"tema_general\":\"texto\","
            "\"pendientes\":[\"item\"],"
            "\"fechas_entrega\":[{\"fecha\":\"YYYY-MM-DD|NO_DATA\",\"detalle\":\"texto\"}],"
            "\"personas_mencionadas\":[{\"nombre\":\"texto\",\"motivo\":\"texto\"}],"
            "\"promesas_pago\":[{\"valor\":\"texto\",\"fecha\":\"YYYY-MM-DD|NO_DATA\",\"detalle\":\"texto\"}],"
            "\"no_respondido\":true|false"
            "}\n"
            "transcript:\n"
            f"{transcript}"
        )

    def _build_month_prompt(self, user: ChatUser, month_start: date, transcript: str, unresolved_count: int) -> str:
        return (
            "Eres un analista CRM comercial riguroso. Resume SOLO con evidencia literal consolidada de resúmenes diarios. "
            "Si no hay evidencia, responde 'NO_DATA'. Salida SOLO JSON valido sin markdown. "
            "Genera un informe ejecutivo explícito, concreto y accionable.\n"
            f"usuario: {user.display_label()}\n"
            f"mes_objetivo: {month_start.year}-{month_start.month:02d}\n"
            f"mensajes_no_respondidos_detectados: {unresolved_count}\n"
            "schema={"
            "\"de_que_se_habla\":\"tema principal con contexto\","
            "\"problema_central\":\"bloqueo principal concreto\","
            "\"estado_comercial\":\"frio|activo|en cierre|riesgo + justificacion\","
            "\"que_pide_exactamente_el_cliente\":\"pedido textual y concreto\","
            "\"que_respondio_el_equipo\":\"respuesta real del equipo\","
            "\"proximos_pasos\":[\"accion concreta con responsable o fecha\"],"
            "\"evidencias\":[\"cita breve literal del resumen diario\"],"
            "\"resumen_ejecutivo\":\"maximo 280 palabras\","
            "\"tema_general\":\"texto\","
            "\"pendientes\":[\"item\"],"
            "\"fechas_entrega\":[{\"fecha\":\"YYYY-MM-DD|NO_DATA\",\"detalle\":\"texto\"}],"
            "\"personas_mencionadas\":[{\"nombre\":\"texto\",\"motivo\":\"texto\"}],"
            "\"promesas_pago\":[{\"valor\":\"texto\",\"fecha\":\"YYYY-MM-DD|NO_DATA\",\"detalle\":\"texto\"}],"
            "\"no_respondido\":true|false"
            "}\n"
            "transcript_mensual_desde_resumenes_diarios:\n"
            f"{transcript}"
        )

    def _call_model(self, prompt: str, summary_kind: str = "day", source_context: str = "") -> SummaryResult:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "num_predict": 320,
            },
        }
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        raw_response = data.get("response") or "{}"
        parsed = self._safe_json_load(raw_response)

        if summary_kind == "month":
            summary = self._compose_monthly_executive_text(parsed, raw_response, source_context)
        else:
            summary = str(parsed.get("resumen_corto") or "").strip()
            if not summary or summary.upper() == "NO_DATA":
                fallback_text = self._extract_fallback_text(raw_response)
                summary = fallback_text if fallback_text else "NO_DATA"

        summary = self._collapse_repeated_clauses(summary)
        if str(summary).strip().upper() in {"NO_DATA", "NO DATA", "NO-DATA", "NO_DATA."}:
            summary = "NO_DATA"

        if summary == "":
            summary = "NO_DATA"

        pending_items = self._normalize_string_list(parsed.get("pendientes"))
        mentioned_people = self._normalize_named_items(parsed.get("personas_mencionadas"), ["nombre", "motivo"])
        deadlines = self._normalize_named_items(parsed.get("fechas_entrega"), ["fecha", "detalle"])
        payment_promises = self._normalize_named_items(parsed.get("promesas_pago"), ["valor", "fecha", "detalle"])

        prompt_tokens = int(data.get("prompt_eval_count") or data.get("prompt_tokens") or 0)
        completion_tokens = int(data.get("eval_count") or data.get("completion_tokens") or 0)
        total_tokens = int(data.get("total_tokens") or (prompt_tokens + completion_tokens))

        has_data = str(summary).strip().upper() != "NO_DATA"
        return SummaryResult(
            text=summary,
            has_data=has_data,
            pending_items=pending_items,
            mentioned_people=mentioned_people,
            deadlines=deadlines,
            payment_promises=payment_promises,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            raw=parsed,
        )

    def _compose_monthly_executive_text(self, parsed: dict[str, Any], raw_response: str = "", source_context: str = "") -> str:
        def _sanitize(value: str) -> str:
            txt = str(value or "").strip()
            if not txt:
                return "NO_DATA"

            lowered = txt.lower()
            noisy_tokens = [
                "schema",
                "maximo 280 palabras",
                "maximo 220 palabras",
                "resumen_ejecutivo",
                "de_que_se_habla",
                "problema_central",
                "no se proporciona resumen ejecutivo",
            ]
            if txt.startswith("{") or txt.startswith("["):
                return "NO_DATA"
            if any(tok in lowered for tok in noisy_tokens):
                return "NO_DATA"
            if lowered in {"no_data", "none", "null", "nan"}:
                return "NO_DATA"
            return txt

        def _read(key: str) -> str:
            return _sanitize(parsed.get(key) or "")

        digest_fallback = self._extract_month_fallback_from_digest(source_context)
        last_response_day = digest_fallback.get("last_response_day", "NO_DATA")

        de_que = _read("de_que_se_habla")
        problema = _read("problema_central")
        estado = _read("estado_comercial")
        pedido = _read("que_pide_exactamente_el_cliente")
        respuesta = _read("que_respondio_el_equipo")
        ejecutivo = _read("resumen_ejecutivo")

        proximos = self._normalize_string_list(parsed.get("proximos_pasos"))
        evidencias = self._normalize_string_list(parsed.get("evidencias"))
        pendientes = self._normalize_string_list(parsed.get("pendientes"))
        no_respondido = bool(parsed.get("no_respondido"))
        tema_general = _read("tema_general")

        # Compatibilidad con respuestas antiguas o parciales del modelo.
        if de_que == "NO_DATA":
            de_que = _sanitize(tema_general)
        if de_que == "NO_DATA":
            de_que = digest_fallback.get("tema", "NO_DATA")
        if ejecutivo == "NO_DATA":
            ejecutivo = _read("resumen_corto")
        if ejecutivo == "NO_DATA":
            ejecutivo = digest_fallback.get("resumen_ejecutivo", "NO_DATA")
        if problema == "NO_DATA":
            problema = _sanitize(tema_general)
        if problema == "NO_DATA":
            problema = digest_fallback.get("problema", "NO_DATA")

        if not evidencias:
            resumen_corto = str(parsed.get("resumen_corto") or "").strip()
            if resumen_corto and resumen_corto.upper() != "NO_DATA":
                evidencias = [resumen_corto]

        if ejecutivo == "NO_DATA":
            fallback_text = self._extract_fallback_text(raw_response)
            if fallback_text:
                ejecutivo = _sanitize(fallback_text)

        # Fallback semántico para evitar bloques vacíos cuando sí hay contexto.
        if de_que == "NO_DATA" and ejecutivo != "NO_DATA":
            de_que = ejecutivo
        if problema == "NO_DATA" and ejecutivo != "NO_DATA":
            problema = ejecutivo
        if estado == "NO_DATA":
            if no_respondido:
                if last_response_day != "NO_DATA":
                    estado = f"riesgo por falta de respuesta del equipo desde el {last_response_day}"
                else:
                    estado = "riesgo por falta de respuesta del equipo en el periodo analizado"
            elif tema_general != "NO_DATA":
                estado = f"activo con seguimiento sobre: {tema_general}"
            elif ejecutivo != "NO_DATA":
                estado = "activo con información parcial consolidada"
        if pedido == "NO_DATA":
            if pendientes:
                pedido = pendientes[0]
            elif digest_fallback.get("pedido"):
                pedido = digest_fallback["pedido"]
            elif ejecutivo != "NO_DATA":
                pedido = "Ver resumen ejecutivo para detalle del pedido"
        if respuesta == "NO_DATA":
            if no_respondido:
                if last_response_day != "NO_DATA":
                    respuesta = f"No hay respuesta nuestra desde el {last_response_day}"
                else:
                    respuesta = "No hay respuesta nuestra en el periodo consolidado"
            elif digest_fallback.get("respuesta"):
                respuesta = digest_fallback["respuesta"]
            elif ejecutivo != "NO_DATA":
                respuesta = "Respuesta parcial identificada; revisar evidencias"
        if not proximos:
            if pendientes:
                proximos = [f"Atender pendiente: {item}" for item in pendientes[:4]]
            elif no_respondido:
                proximos = ["Responder al cliente con confirmación y siguiente hito"]
            elif digest_fallback.get("proximo"):
                proximos = [digest_fallback["proximo"]]

        cleaned_proximos = [p for p in (_sanitize(x) for x in proximos) if p != "NO_DATA"]
        cleaned_evidencias = [e for e in (_sanitize(x) for x in evidencias) if e != "NO_DATA"]

        if all(x == "NO_DATA" for x in [de_que, problema, estado, pedido, respuesta, ejecutivo]) and not cleaned_proximos and not cleaned_evidencias:
            return "NO_DATA"

        # Evita repetir el mismo texto en varias secciones.
        if problema != "NO_DATA" and de_que != "NO_DATA" and problema.lower() == de_que.lower():
            if pedido != "NO_DATA":
                problema = f"Pendiente principal: {pedido}"
            elif no_respondido:
                problema = "Falta respuesta o cierre por parte del equipo"

        compact_parts = []
        if de_que != "NO_DATA":
            compact_parts.append(f"Tema: {de_que}")
        if problema != "NO_DATA":
            compact_parts.append(f"Problema: {problema}")
        if pedido != "NO_DATA":
            compact_parts.append(f"Cliente pide: {pedido}")
        if respuesta != "NO_DATA":
            compact_parts.append(f"Equipo respondió: {respuesta}")
        if cleaned_proximos:
            compact_parts.append(f"Próximo paso: {cleaned_proximos[0]}")
        elif estado != "NO_DATA":
            compact_parts.append(f"Estado: {estado}")

        if len(compact_parts) < 2 and ejecutivo != "NO_DATA":
            return self._collapse_repeated_clauses(f"Resumen mensual: {ejecutivo}")
        return self._collapse_repeated_clauses(" | ".join(compact_parts[:5]))

    def _extract_month_fallback_from_digest(self, source_context: str) -> dict[str, str]:
        lines = [ln.strip() for ln in (source_context or "").splitlines() if ln.strip()]
        summaries: list[str] = []
        pendings: list[str] = []
        last_response_day = "NO_DATA"
        for line in lines:
            m = re.search(r"resumen_dia:\s*(.*?)\s*\|\s*pendientes:\s*(.*?)\s*\|", line, flags=re.IGNORECASE)
            if m:
                s = (m.group(1) or "").strip()
                p = (m.group(2) or "").strip()
                if s and s.upper() != "NO_DATA":
                    summaries.append(s)
                    low = s.lower()
                    response_markers = (
                        "con respuesta",
                        "respuesta parcial",
                        "respuesta por audio",
                        "respondió",
                        "respondio",
                    )
                    if any(marker in low for marker in response_markers):
                        day_match = re.match(r"^(\d{4}-\d{2}-\d{2})\s*\|", line)
                        if day_match:
                            last_response_day = day_match.group(1)
                if p and p.upper() != "NO_DATA":
                    pendings.append(p)

        tema = summaries[0] if summaries else "NO_DATA"
        pedido = pendings[0] if pendings else "NO_DATA"
        problema = "NO_DATA"
        if pedido != "NO_DATA":
            problema = f"Pendiente abierto: {pedido}"
        elif summaries:
            low = " ".join(summaries).lower()
            if "no respond" in low:
                problema = "Seguimiento sin respuesta clara del equipo"

        respuesta = "NO_DATA"
        if summaries:
            low = " ".join(summaries).lower()
            if "no respond" in low:
                respuesta = "No se evidencia respuesta suficiente del equipo"
            elif "respond" in low or "confirm" in low:
                respuesta = "Se observa respuesta parcial del equipo"

        proximo = "NO_DATA"
        if pedido != "NO_DATA":
            proximo = f"Cerrar pendiente: {pedido}"
        elif tema != "NO_DATA":
            proximo = "Confirmar próximo hito y fecha con el cliente"

        resumen_ejecutivo = "NO_DATA"
        if tema != "NO_DATA":
            resumen_ejecutivo = tema

        return {
            "tema": self._collapse_repeated_clauses(tema),
            "problema": self._collapse_repeated_clauses(problema),
            "pedido": self._collapse_repeated_clauses(pedido),
            "respuesta": self._collapse_repeated_clauses(respuesta),
            "proximo": self._collapse_repeated_clauses(proximo),
            "resumen_ejecutivo": self._collapse_repeated_clauses(resumen_ejecutivo),
            "last_response_day": self._collapse_repeated_clauses(last_response_day),
        }

    def _collapse_repeated_clauses(self, text: str) -> str:
        raw = str(text or "").strip()
        if not raw:
            return "NO_DATA"
        if raw == "NO_DATA":
            return raw

        parts = [p.strip() for p in re.split(r"\s*\|\s*|(?<=[.!?])\s+", raw) if p.strip()]
        if not parts:
            return raw

        deduped: list[str] = []
        seen = set()
        for part in parts:
            normalized = re.sub(r"\s+", " ", part).strip().lower()
            if not normalized:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(part)

        collapsed = " | ".join(deduped[:8]).strip()
        return collapsed or raw

    def _extract_fallback_text(self, raw_response: str) -> str:
        text = str(raw_response or "").strip()
        if not text:
            return ""

        # Si vino un JSON serializado como texto pero no parseable completo, intenta recuperar campos claves.
        lowered = text.lower()
        if "resumen_corto" in lowered or "resumen_ejecutivo" in lowered:
            for key in ["resumen_ejecutivo", "resumen_corto", "tema_general"]:
                token = f'"{key}"'
                idx = lowered.find(token)
                if idx >= 0:
                    after = text[idx + len(token):]
                    colon = after.find(":")
                    if colon >= 0:
                        value = after[colon + 1 :].strip().lstrip('"').split('"', 1)[0].strip()
                        if value and value.upper() != "NO_DATA":
                            return value

        compact = " ".join(text.split())
        if compact.startswith("{") and compact.endswith("}"):
            return ""
        return compact[:500]

    def _empty_result(self, text: str) -> SummaryResult:
        return SummaryResult(
            text=text,
            has_data=False,
            pending_items=[],
            mentioned_people=[],
            deadlines=[],
            payment_promises=[],
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            raw={},
        )

    def _safe_json_load(self, text: str) -> dict:
        content = str(text or "{}").strip()
        if not content:
            return {}
        try:
            loaded = json.loads(content)
            return loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            # Recupera primer bloque JSON valido cuando el modelo devuelve prefijos/sufijos extra.
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                candidate = content[start : end + 1]
                try:
                    loaded = json.loads(candidate)
                    return loaded if isinstance(loaded, dict) else {}
                except json.JSONDecodeError:
                    return {}
            return {}

    def _normalize_string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        out = []
        blocked = {"", "no_data", "no data", "none", "null", "item", "n/a"}
        for item in value:
            txt = str(item or "").strip()
            if txt and txt.lower() not in blocked:
                out.append(txt)
        return out

    def _normalize_named_items(self, value: Any, keys: list[str]) -> list[dict[str, str]]:
        if not isinstance(value, list):
            return []
        out: list[dict[str, str]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            normalized = {}
            all_no_data = True
            for key in keys:
                val = str(item.get(key) or "NO_DATA").strip() or "NO_DATA"
                if val.upper() not in {"NO_DATA", "NO DATA", "NONE", "NULL", "N/A"}:
                    all_no_data = False
                normalized[key] = val
            if not all_no_data:
                out.append(normalized)
        return out


def compute_due_slots(now: datetime, lookback_hours: int = 48) -> list[tuple[datetime, datetime, str]]:
    """Retorna slots de 12h anclados a 10:00 y 22:00 UTC pendientes de procesar."""
    end = now.replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(hours=lookback_hours)
    slots: list[tuple[datetime, datetime, str]] = []

    cursor = start.replace(hour=10)
    if cursor > start:
        cursor -= timedelta(days=1)

    while cursor < end:
        slot_start = cursor
        slot_end = cursor + timedelta(hours=12)
        if slot_end > start and slot_start < end:
            key = f"{slot_start.strftime('%Y%m%d%H')}_{slot_end.strftime('%Y%m%d%H')}"
            slots.append((slot_start, slot_end, key))
        cursor = slot_end

    return slots


def should_run_now(now: datetime, tolerance_minutes: int = 20) -> bool:
    hour = now.hour
    if hour not in (10, 22):
        return False
    return now.minute <= tolerance_minutes
