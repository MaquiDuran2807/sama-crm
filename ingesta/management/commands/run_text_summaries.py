from django.core.management import BaseCommand
from django.utils import timezone

from ingesta.models import EvolutionInstance, SummaryExecutionControl
from ingesta.services import IngestionService
from ingesta.summary_service import (TextSummaryService, compute_due_slots,
                                     should_run_now)


class Command(BaseCommand):
    help = (
        "Sincroniza ingesta y genera resumenes IA de texto diarios y mensuales "
        "en ventanas de 12h (10:00 y 22:00)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--lookback-hours",
            type=int,
            default=48,
            help="Horas hacia atras para detectar slots pendientes. Por defecto 48 (dos dias).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Reprocesa slots aunque ya esten en COMPLETED.",
        )
        parser.add_argument(
            "--skip-ingestion",
            action="store_true",
            help="No corre sincronizacion previa de ingesta.",
        )
        parser.add_argument(
            "--only-current-slot",
            action="store_true",
            help="Solo corre cuando la hora actual este en ventana 10:00/22:00.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        force = bool(options["force"])
        lookback_hours = int(options["lookback_hours"])
        skip_ingestion = bool(options["skip_ingestion"])
        only_current_slot = bool(options["only_current_slot"])

        if only_current_slot and not should_run_now(now):
            self.stdout.write("Fuera de ventana 10:00/22:00. No se ejecuta.")
            return

        if not skip_ingestion:
            self._run_ingestion()

        summary_service = TextSummaryService()
        slots = compute_due_slots(now=now, lookback_hours=lookback_hours)
        if not slots:
            self.stdout.write("No hay slots pendientes por evaluar.")
            return

        ran = 0
        skipped_completed = 0
        for slot_start, slot_end, key in slots:
            run_key = f"summary_{key}"
            existing = SummaryExecutionControl.objects.filter(run_key=run_key).first()
            if existing and existing.status == SummaryExecutionControl.Status.COMPLETED and not force:
                skipped_completed += 1
                continue

            log = summary_service.run_for_slot(
                slot_start=slot_start,
                slot_end=slot_end,
                run_key=run_key,
                force=force,
            )
            ran += 1
            self.stdout.write(
                f"Slot {slot_start.isoformat()} -> {slot_end.isoformat()} | "
                f"status={log.status} users={log.processed_users}/{log.eligible_users} "
                f"tokens={log.total_tokens}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Proceso terminado. corridos={ran} | omitidos_por_completado={skipped_completed}"
            )
        )

    def _run_ingestion(self):
        instances = list(EvolutionInstance.objects.filter(is_active=True).order_by("instance_name"))
        if not instances:
            self.stdout.write("Sin instancias activas para sincronizar.")
            return

        self.stdout.write("Ejecutando sincronizacion previa de ingesta...")
        for instance in instances:
            service = IngestionService(instance_name=instance.instance_name)
            result = service.sync_messages()
            self.stdout.write(
                f"Ingesta {instance.instance_name}: fetched={result.get('fetched', 0)} "
                f"inserted={result.get('inserted', 0)}"
            )
