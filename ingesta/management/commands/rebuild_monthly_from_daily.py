from django.core.management import BaseCommand
from django.db.models import Sum

from ingesta.models import DailyTextSummary, MonthlyTextSummary
from ingesta.summary_service import TextSummaryService


class Command(BaseCommand):
    help = (
        "Reprocesa resúmenes mensuales desde resúmenes diarios existentes "
        "(sin re-leer todos los mensajes crudos)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Fuerza nueva revisión mensual aunque el origen no haya cambiado.",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            default=None,
            help="Filtra por user_id específico.",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=None,
            help="Filtra por año (YYYY).",
        )
        parser.add_argument(
            "--month",
            type=int,
            default=None,
            help="Filtra por mes (1-12).",
        )
        parser.add_argument(
            "--no-report",
            action="store_true",
            help="No imprime el reporte detallado final por usuario/mes.",
        )

    def handle(self, *args, **options):
        force = bool(options["force"])
        user_id = options.get("user_id")
        year = options.get("year")
        month = options.get("month")
        no_report = bool(options.get("no_report"))

        run_key = "rebuild_monthly_from_daily"
        if user_id:
            run_key += f"_u{user_id}"
        if year:
            run_key += f"_{year}"
        if month:
            run_key += f"_{int(month):02d}"

        service = TextSummaryService()
        log = service.rebuild_monthly_summaries_from_daily(
            run_key=run_key,
            force=force,
            user_id=user_id,
            year=year,
            month=month,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"status={log.status} | processed_users={log.processed_users} | "
                f"failed_users={log.failed_users} | monthly_created={log.monthly_summaries_created} | "
                f"monthly_updated={log.monthly_summaries_updated} | tokens={log.total_tokens}"
            )
        )

        if not no_report:
            self._print_detailed_report(user_id=user_id, year=year, month=month)

    def _print_detailed_report(self, user_id: int | None, year: int | None, month: int | None) -> None:
        daily_qs = DailyTextSummary.objects.select_related("user").all()
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

        if not month_pairs:
            self.stdout.write("\n[Reporte] Sin datos diarios para construir mensual en los filtros indicados.")
            return

        self.stdout.write("\n[Reporte detallado de construcción mensual]")
        for user_pk, y, m in month_pairs:
            month_daily = daily_qs.filter(user_id=user_pk, summary_date__year=y, summary_date__month=m).order_by("summary_date")
            if not month_daily.exists():
                continue

            first_daily = month_daily.first()
            user_label = first_daily.user.name or first_daily.user.phone_number or first_daily.user.wa_id
            monthly = (
                MonthlyTextSummary.objects.filter(user_id=user_pk, year=y, month=m, is_current=True)
                .order_by("-revision")
                .first()
            )

            daily_token_sum = month_daily.aggregate(total=Sum("total_tokens")).get("total") or 0
            daily_count = month_daily.count()
            message_count_sum = month_daily.aggregate(total=Sum("source_message_count")).get("total") or 0

            self.stdout.write("-" * 90)
            self.stdout.write(
                f"chat={user_label} | user_id={user_pk} | mes={y}-{int(m):02d} | "
                f"dias_usados={daily_count} | mensajes_base_diarios={message_count_sum} | tokens_diarios={daily_token_sum}"
            )

            for row in month_daily:
                snippet = (row.text or "").replace("\n", " ")[:120]
                self.stdout.write(
                    f"  dia={row.summary_date} | has_data={row.has_data} | msgs={row.source_message_count} | "
                    f"tokens={row.total_tokens} | resumen={snippet}"
                )

            if monthly:
                monthly_text = (monthly.text or "").replace("\n", " ")[:260]
                self.stdout.write(
                    f"  MONTHLY_ACTUAL r{monthly.revision} | has_data={monthly.has_data} | "
                    f"msgs_base={monthly.source_message_count} | tokens={monthly.total_tokens}"
                )
                self.stdout.write(f"  MONTHLY_TEXTO: {monthly_text}")
            else:
                self.stdout.write("  MONTHLY_ACTUAL: NO_DATA")
