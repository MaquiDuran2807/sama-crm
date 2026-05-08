import os
import sys

from django.apps import AppConfig


class IngestaConfig(AppConfig):
    name = 'ingesta'

    def ready(self):
        management_commands_to_skip = {
            "makemigrations",
            "migrate",
            "collectstatic",
            "shell",
            "test",
            "createsuperuser",
            "run_text_summaries",
            "fetch_evolution_messages",
            "decode_media_backfill",
            "ingesta_dry_run",
        }
        current_args = set(sys.argv)
        if current_args & management_commands_to_skip:
            return

        is_runserver = "runserver" in current_args
        force_enable = os.environ.get("AI_SUMMARY_FORCE_STARTUP", "").strip() == "1"
        if not is_runserver and not force_enable:
            return

        from .scheduler import start_summary_scheduler

        start_summary_scheduler()
