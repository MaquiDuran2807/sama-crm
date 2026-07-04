import logging
from datetime import timedelta
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.core.management import call_command

from .models import ChatUser
from .services import IngestionService
from .summary_service import TextSummaryService
from .audio_service import AudioBriefingService

logger = logging.getLogger(__name__)

@shared_task(bind=True, name="ingesta.tasks.sync_messages_task")
def sync_messages_task(self, instance_name: str = "default"):
    service = IngestionService(instance_name=instance_name)
    
    def on_progress(percent, message):
        self.update_state(state='PROGRESS', meta={'progress': percent, 'message': message})
        
    self.update_state(state='PROGRESS', meta={'progress': 1, 'message': 'Iniciando tarea'})
    result = service.sync_messages(progress_callback=on_progress)
    return result

@shared_task(bind=True, name="ingesta.tasks.run_text_summaries_task")
def run_text_summaries_task(self, lookback_hours: int = 12, force: bool = False, accumulate: bool = True):
    self.update_state(state='PROGRESS', meta={'progress': 10, 'message': 'Iniciando resúmenes IA'})
    
    now = timezone.now()
    slot_end = now
    
    service = TextSummaryService()
    if accumulate:
        slot_start, window_meta = service.compute_accumulation_window(
            slot_end=slot_end,
            fallback_lookback_hours=lookback_hours,
        )
    else:
        slot_start = slot_end - timedelta(hours=lookback_hours)
        window_meta = {
            "mode": "fixed_lookback",
            "today_start": None,
            "oldest_pending_day": None,
            "has_today_text": None,
        }

    run_key = f"manual_{self.request.id}"

    mode_label = {
        "accumulation_pending_backlog": "acumulacion historica + hoy",
        "today_refresh": "actualizacion de hoy",
        "fallback_lookback": "ventana fallback",
        "fixed_lookback": "ventana fija",
    }.get(window_meta.get("mode"), "procesamiento")

    self.update_state(
        state='PROGRESS',
        meta={
            "progress": 15,
            "message": f"Preparando {mode_label}",
        }
    )

    def on_summary_progress(state):
        total = max(1, int(state.get("eligible_users") or 0))
        done = int(state.get("processed_users") or 0) + int(state.get("failed_users") or 0) + int(state.get("skipped_users") or 0)
        if state.get("phase") == "processing_days":
            current_user_index = int(state.get("current_user_index") or 1)
            day_total = max(1, int(state.get("current_user_total_days") or 1))
            day_done = max(0, min(day_total, int(state.get("current_user_day_done") or 0)))
            effective_done = min(total, (current_user_index - 1) + (day_done / day_total))
        else:
            effective_done = done

        pct = 15 + int((effective_done / total) * 80)
        pct = max(15, min(95, pct))
        self.update_state(
            state='PROGRESS',
            meta={
                "progress": pct,
                "message": f"Resumiendo usuarios ({done}/{total}) - {mode_label}",
            }
        )

    log = service.run_for_slot(
        slot_start=slot_start,
        slot_end=slot_end,
        run_key=run_key,
        force=force,
        progress_callback=on_summary_progress,
    )
    log.meta = {
        **(log.meta or {}),
        **window_meta,
    }
    log.save(update_fields=["meta"])
    
    daily_rows = list(log.daily_summaries.select_related("user").order_by("user_id", "summary_date"))
    monthly_rows = list(log.monthly_summaries.select_related("user").order_by("user_id", "year", "month", "-revision"))

    daily_report = []
    for row in daily_rows:
        label = row.user.name or row.user.phone_number or row.user.wa_id
        daily_report.append(
            {
                "user_id": row.user_id,
                "chat": label,
                "date": row.summary_date.isoformat(),
                "has_data": row.has_data,
                "source_message_count": row.source_message_count,
                "tokens": row.total_tokens,
                "text": row.text,
            }
        )

    monthly_report = []
    for row in monthly_rows:
        label = row.user.name or row.user.phone_number or row.user.wa_id
        monthly_report.append(
            {
                "user_id": row.user_id,
                "chat": label,
                "year": row.year,
                "month": row.month,
                "revision": row.revision,
                "has_data": row.has_data,
                "source_message_count": row.source_message_count,
                "tokens": row.total_tokens,
                "text": row.text,
            }
        )

    result = {
        "run_key": log.run_key,
        "status": log.status,
        "eligible_users": log.eligible_users,
        "processed_users": log.processed_users,
        "failed_users": log.failed_users,
        "daily_summaries_created": log.daily_summaries_created,
        "daily_summaries_updated": log.daily_summaries_updated,
        "monthly_summaries_created": log.monthly_summaries_created,
        "monthly_summaries_updated": log.monthly_summaries_updated,
        "total_tokens": log.total_tokens,
        "slot_start": slot_start.isoformat(),
        "slot_end": slot_end.isoformat(),
        "window_mode": window_meta.get("mode"),
        "window_oldest_pending_day": window_meta.get("oldest_pending_day"),
        "window_has_today_text": window_meta.get("has_today_text"),
        "window_step_hours": window_meta.get("accumulation_step_hours"),
        "window_cursor_start": window_meta.get("accumulation_cursor_start"),
        "window_reached_oldest": window_meta.get("accumulation_reached_oldest"),
        "daily_generated": daily_report,
        "monthly_generated": monthly_report,
    }
    return result

@shared_task(bind=True, name="ingesta.tasks.generate_audio_briefing_task")
def generate_audio_briefing_task(self, instance_name: str = "default", team_user_id: int | None = None):
    self.update_state(state='PROGRESS', meta={'progress': 10, 'message': 'Inicializando audio briefing'})

    team_user = None
    if team_user_id:
        team_user = ChatUser.objects.filter(id=team_user_id).first()
        if not team_user:
            self.update_state(
                state='PROGRESS',
                meta={
                    "progress": 12,
                    "message": f"team_user_id={team_user_id} no existe, usando fallback automático",
                }
            )

    if not team_user:
        team_user = ChatUser.objects.filter(is_customer=False).order_by("-last_interaction", "id").first()

    if not team_user:
        team_user = ChatUser.objects.order_by("-last_interaction", "id").first()

    if not team_user:
        raise ValueError("No hay usuario de equipo disponible para generar el briefing")

    service = AudioBriefingService()

    def on_audio_progress(state: dict):
        pct = max(10, min(95, int(state.get("progress") or 10)))
        phase = str(state.get("phase") or "proceso")
        detail = str(state.get("detail") or "")
        self.update_state(
            state='PROGRESS',
            meta={
                "progress": pct,
                "message": f"Audio briefing [{phase}] {detail}".strip(),
            }
        )

    result = service.generate_daily_briefing(
        instance_name=instance_name,
        team_user=team_user,
        date=timezone.now(),
        force_local_only=True,
        progress_callback=on_audio_progress,
    )

    if result.get("error"):
        raise RuntimeError(result["error"])

    audio_file = str(result.get("audio_file") or "").lstrip("/")
    media_url = str(getattr(settings, "MEDIA_URL", "/media/") or "/media/")
    if not media_url.endswith("/"):
        media_url = f"{media_url}/"
    if audio_file:
        result["audio_download_url"] = f"{media_url}{audio_file}"
    result["selected_team_user"] = {
        "id": team_user.id,
        "display_label": team_user.display_label(),
    }
    result["delivery_mode"] = "download_only"
    return result

@shared_task(name="ingesta.tasks.ai_summary_periodic_task")
def ai_summary_periodic_task():
    logger.info("Iniciando tarea periódica de resúmenes de texto IA (Celery Beat)")
    call_command("run_text_summaries", lookback_hours=24, only_current_slot=True)
