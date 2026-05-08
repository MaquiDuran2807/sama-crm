from datetime import timedelta

from django.core.management import BaseCommand
from django.db import transaction
from django.utils import timezone

from ingesta.models import (DailyTextSummary, Message, MonthlyTextSummary,
                            SummaryExecutionControl)
from ingesta.summary_service import TextSummaryService


class Command(BaseCommand):
    help = "Purga resúmenes generados y los reconstruye desde cero evitando duplicados visibles."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=None,
            help="Año objetivo a reconstruir (opcional). Si no se indica, usa todo el histórico.",
        )
        parser.add_argument(
            "--month",
            type=int,
            default=None,
            help="Mes objetivo a reconstruir (opcional). Requiere --year si se usa.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo muestra qué se borraría y reconstruiría, sin cambios.",
        )

    def handle(self, *args, **options):
        year = options.get("year")
        month = options.get("month")
        dry_run = bool(options.get("dry_run"))

        if month and not year:
            raise SystemExit("Si usas --month debes indicar también --year.")

        msg_qs = Message.objects.filter(message_type=Message.MessageType.TEXT)
        if year:
            msg_qs = msg_qs.filter(timestamp__year=year)
        if month:
            msg_qs = msg_qs.filter(timestamp__month=month)

        min_ts = msg_qs.order_by("timestamp").values_list("timestamp", flat=True).first()
        max_ts = msg_qs.order_by("-timestamp").values_list("timestamp", flat=True).first()

        self.stdout.write("[reset_and_rebuild_summaries]")
        self.stdout.write(f"- filtros: year={year} month={month}")
        self.stdout.write(f"- rango_detectado: {min_ts} -> {max_ts}")
        self.stdout.write(f"- diarios_actuales: {DailyTextSummary.objects.count()}")
        self.stdout.write(f"- mensuales_actuales: {MonthlyTextSummary.objects.count()}")
        self.stdout.write(f"- ejecuciones_actuales: {SummaryExecutionControl.objects.count()}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN: no se realizaron cambios."))
            return

        daily_delete_qs = DailyTextSummary.objects.all()
        monthly_delete_qs = MonthlyTextSummary.objects.all()
        exec_delete_qs = SummaryExecutionControl.objects.all()

        if year:
            daily_delete_qs = daily_delete_qs.filter(summary_date__year=year)
            monthly_delete_qs = monthly_delete_qs.filter(year=year)
            exec_delete_qs = exec_delete_qs.filter(slot_start__year=year)
        if month:
            daily_delete_qs = daily_delete_qs.filter(summary_date__month=month)
            monthly_delete_qs = monthly_delete_qs.filter(month=month)
            exec_delete_qs = exec_delete_qs.filter(slot_start__month=month)

        with transaction.atomic():
            daily_delete_qs.delete()
            monthly_delete_qs.delete()
            exec_delete_qs.delete()

        service = TextSummaryService()

        if not min_ts or not max_ts:
            self.stdout.write(self.style.WARNING("No hay mensajes de texto en el rango seleccionado. Nada para reconstruir."))
            return

        start = min_ts.replace(hour=0, minute=0, second=0, microsecond=0)
        end = (max_ts + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        self.stdout.write(f"- rebuild_diario_slot: {start} -> {end}")
        daily_log = service.run_for_slot(
            slot_start=start,
            slot_end=end,
            run_key=f"reset_daily_{start.date().isoformat()}_{end.date().isoformat()}",
            force=True,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"daily_status={daily_log.status} | processed={daily_log.processed_users} | "
                f"failed={daily_log.failed_users} | daily_created={daily_log.daily_summaries_created} | "
                f"daily_updated={daily_log.daily_summaries_updated} | tokens={daily_log.total_tokens}"
            )
        )

        monthly_log = service.rebuild_monthly_summaries_from_daily(
            run_key=f"reset_monthly_{start.date().isoformat()}_{end.date().isoformat()}",
            force=True,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"monthly_status={monthly_log.status} | processed={monthly_log.processed_users} | "
                f"failed={monthly_log.failed_users} | monthly_created={monthly_log.monthly_summaries_created} | "
                f"monthly_updated={monthly_log.monthly_summaries_updated} | tokens={monthly_log.total_tokens}"
            )
        )
