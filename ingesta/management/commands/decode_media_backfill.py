from django.core.management.base import BaseCommand
from urllib.parse import urlparse
from collections import Counter

from ingesta.models import Message
from ingesta.services import IngestionService


class Command(BaseCommand):
    help = "Decodifica/descarga media historica (incluye .enc via Evolution) y guarda media_file en Message."

    def add_arguments(self, parser):
        parser.add_argument("--instance", default="Deya3", help="Nombre de instancia Evolution")
        parser.add_argument("--limit", type=int, default=0, help="Maximo de mensajes a procesar (0 = sin limite)")
        parser.add_argument("--batch-size", type=int, default=500, help="Tamanio de lote para modo auto-loop")
        parser.add_argument("--auto-loop", action="store_true", help="Ejecuta lotes hasta vaciar pendientes")
        parser.add_argument("--max-batches", type=int, default=0, help="Maximo de lotes en auto-loop (0 = sin limite)")
        parser.add_argument(
            "--types",
            default="audio,image,video",
            help="Tipos de mensaje separados por coma (audio,image,video)",
        )
        parser.add_argument(
            "--only-enc",
            action="store_true",
            help="Procesar solo registros con media_url .enc",
        )
        parser.add_argument(
            "--fail-log",
            default="",
            help="Ruta de archivo para registrar fallos (CSV simple)",
        )
        parser.add_argument(
            "--require-raw-data",
            action="store_true",
            help="En media .enc, omite mensajes sin raw_data para evitar intentos imposibles",
        )
        parser.add_argument(
            "--verbose-errors",
            action="store_true",
            help="Imprime detalle tecnico por cada fallo (status HTTP, fase, excepcion)",
        )

    def handle(self, *args, **options):
        instance_name = options["instance"].strip()
        limit = int(options["limit"] or 0)
        batch_size = max(1, int(options["batch_size"] or 500))
        auto_loop = bool(options.get("auto_loop"))
        max_batches = max(0, int(options.get("max_batches") or 0))
        allowed_types = [t.strip() for t in str(options["types"]).split(",") if t.strip()]
        only_enc = bool(options.get("only_enc"))
        fail_log = str(options.get("fail_log") or "").strip()
        require_raw_data = bool(options.get("require_raw_data"))
        verbose_errors = bool(options.get("verbose_errors"))

        service = IngestionService(instance_name=instance_name)

        def build_queryset():
            qs = (
                Message.objects.filter(message_type__in=allowed_types)
                .exclude(media_url="")
                .filter(media_file="")
                .order_by("-timestamp")
            )
            if only_enc:
                qs = qs.filter(media_url__icontains=".enc")
            if require_raw_data:
                qs = qs.exclude(raw_data__isnull=True).exclude(raw_data={})
            return qs

        processed = 0
        saved = 0
        failed = 0

        fail_writer = None
        fail_file = None
        if fail_log:
            fail_file = open(fail_log, "a", encoding="utf-8")
            fail_writer = fail_file.write

        def process_queryset(qs, batch_label="single"):
            local_processed = 0
            local_saved = 0
            local_failed = 0
            total_local = qs.count()
            fail_reasons = Counter()

            def _safe_text(value):
                return str(value or "").replace("\n", " ").replace("\r", " ").replace(",", ";")

            for msg in qs.iterator(chunk_size=100):
                local_processed += 1
                raw_data = msg.raw_data if isinstance(msg.raw_data, dict) else {}
                media_url = str(msg.media_url or "").strip()
                is_enc = urlparse(media_url).path.lower().endswith(".enc")

                if not media_url:
                    local_failed += 1
                    fail_reasons["NO_MEDIA_URL"] += 1
                    if fail_writer:
                        fail_writer(f"{batch_label},{msg.external_id},NO_MEDIA_URL,{msg.message_type},{msg.media_url}\n")
                    if verbose_errors:
                        self.stdout.write(
                            f"{batch_label} FAIL {msg.external_id}: reason=NO_MEDIA_URL type={msg.message_type}"
                        )
                    continue

                if is_enc and not raw_data:
                    local_failed += 1
                    fail_reasons["MISSING_RAW_DATA"] += 1
                    if fail_writer:
                        fail_writer(f"{batch_label},{msg.external_id},MISSING_RAW_DATA,{msg.message_type},{msg.media_url}\n")
                    if verbose_errors:
                        self.stdout.write(
                            f"{batch_label} FAIL {msg.external_id}: reason=MISSING_RAW_DATA type={msg.message_type}"
                        )
                    continue

                try:
                    debug_meta = {}
                    file_path = service._download_media_file(
                        external_id=msg.external_id,
                        media_url=media_url,
                        media_mime_type=msg.media_mime_type,
                        raw_data=raw_data,
                        debug_info=debug_meta,
                    )
                    if file_path:
                        Message.objects.filter(pk=msg.pk).update(media_file=file_path)
                        local_saved += 1
                    else:
                        local_failed += 1
                        reason = str(debug_meta.get("error") or "DECODE_OR_DOWNLOAD_FAILED")
                        status = str(debug_meta.get("http_status") or "")
                        phase = str(debug_meta.get("phase") or "")
                        exception_type = str(debug_meta.get("exception_type") or "")
                        preview = str(debug_meta.get("response_preview") or debug_meta.get("exception") or "")
                        fail_reasons[reason] += 1
                        if fail_writer:
                            fail_writer(
                                f"{batch_label},{msg.external_id},{_safe_text(reason)},{msg.message_type},{_safe_text(msg.media_url)},{_safe_text(status)},{_safe_text(phase)},{_safe_text(exception_type)},{_safe_text(preview)}\n"
                            )
                        if verbose_errors:
                            self.stdout.write(
                                f"{batch_label} FAIL {msg.external_id}: reason={reason} status={status or '-'} phase={phase or '-'} ex={exception_type or '-'} detail={preview or '-'}"
                            )
                except Exception as ex:
                    local_failed += 1
                    fail_reasons["EXCEPTION"] += 1
                    if fail_writer:
                        fail_writer(
                            f"{batch_label},{msg.external_id},EXCEPTION,{msg.message_type},{_safe_text(msg.media_url)},,,{_safe_text(type(ex).__name__)},{_safe_text(str(ex))}\n"
                        )
                    if verbose_errors:
                        self.stdout.write(
                            f"{batch_label} FAIL {msg.external_id}: reason=EXCEPTION ex={type(ex).__name__} detail={ex}"
                        )

                if local_processed % 50 == 0:
                    self.stdout.write(
                        f"{batch_label} progreso: {local_processed}/{total_local} | guardados={local_saved} | fallidos={local_failed}"
                    )

            if fail_reasons:
                reasons_str = ", ".join(f"{k}={v}" for k, v in fail_reasons.most_common())
                self.stdout.write(f"{batch_label} resumen_errores: {reasons_str}")

            return local_processed, local_saved, local_failed

        if auto_loop:
            self.stdout.write(self.style.WARNING(
                f"Iniciando auto-loop: batch_size={batch_size}, max_batches={max_batches or 'inf'}"
            ))
            batch_index = 0
            while True:
                if max_batches and batch_index >= max_batches:
                    self.stdout.write(self.style.WARNING("Auto-loop detenido por max_batches"))
                    break

                pending_qs = build_queryset()
                pending_total = pending_qs.count()
                if pending_total == 0:
                    self.stdout.write(self.style.SUCCESS("No quedan pendientes por procesar"))
                    break

                batch_index += 1
                batch_qs = pending_qs[:batch_size]
                self.stdout.write(self.style.WARNING(
                    f"Lote {batch_index}: procesando hasta {batch_size} de {pending_total} pendientes"
                ))
                p, s, f = process_queryset(batch_qs, batch_label=f"batch-{batch_index}")
                processed += p
                saved += s
                failed += f

                remaining = build_queryset().count()
                self.stdout.write(
                    self.style.WARNING(
                        f"Lote {batch_index} finalizado: procesados={p} guardados={s} fallidos={f} | restantes={remaining}"
                    )
                )

                if s == 0:
                    self.stdout.write(self.style.WARNING(
                        "Sin avance en el ultimo lote (guardados=0). Se detiene para evitar ciclo infinito."
                    ))
                    break
        else:
            qs = build_queryset()
            if limit > 0:
                qs = qs[:limit]
            total = qs.count()
            self.stdout.write(self.style.WARNING(f"Iniciando backfill de media: {total} mensajes"))
            p, s, f = process_queryset(qs, batch_label="single")
            processed += p
            saved += s
            failed += f

        self.stdout.write(self.style.SUCCESS(
            f"Finalizado. procesados={processed} guardados={saved} fallidos={failed}"
        ))

        if fail_file:
            fail_file.close()
