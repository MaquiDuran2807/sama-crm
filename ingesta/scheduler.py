import logging
import os
import threading
import time

from django.conf import settings
from django.core.management import call_command

logger = logging.getLogger(__name__)

_STARTED = False
_LOCK = threading.Lock()


def start_summary_scheduler() -> None:
    global _STARTED
    with _LOCK:
        if _STARTED:
            return
        _STARTED = True

    if os.environ.get("RUN_MAIN") not in (None, "true"):
        return

    enabled = bool(getattr(settings, "AI_SUMMARY_SCHEDULER_ENABLED", True))
    if not enabled:
        logger.info("AI summary scheduler deshabilitado por settings")
        return

    thread = threading.Thread(target=_scheduler_loop, name="ai-summary-scheduler", daemon=True)
    thread.start()


def _scheduler_loop() -> None:
    startup_lookback = int(getattr(settings, "AI_SUMMARY_STARTUP_LOOKBACK_HOURS", 48))
    interval_seconds = int(getattr(settings, "AI_SUMMARY_CHECK_INTERVAL_SECONDS", 300))

    try:
        logger.info("AI summary scheduler startup catch-up. lookback=%s", startup_lookback)
        call_command("run_text_summaries", lookback_hours=startup_lookback)
    except Exception:
        logger.exception("Fallo en startup catch-up de resumenes IA")

    while True:
        try:
            call_command("run_text_summaries", lookback_hours=24, only_current_slot=True)
        except Exception:
            logger.exception("Fallo en ciclo periodico de resumenes IA")
        time.sleep(interval_seconds)
