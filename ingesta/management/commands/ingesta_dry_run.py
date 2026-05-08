from datetime import datetime, timezone as dt_timezone

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand

from ingesta.models import ChatUser, EvolutionInstance, IngestionControl, Message
from ingesta.services import IngestionService


class Command(BaseCommand):
    help = (
        "Simula una corrida de ingesta sin persistir cambios. "
        "Reporta deduplicacion, altas potenciales y reglas de nombres."
    )

    def add_arguments(self, parser):
        parser.add_argument("--instance", default="Deya3", help="Nombre de instancia Evolution")
        parser.add_argument("--page-size", type=int, default=200, help="Tamano de pagina")
        parser.add_argument("--max-pages", type=int, default=10, help="Maximo de paginas a consultar")
        parser.add_argument(
            "--since-epoch",
            type=int,
            default=None,
            help="Cursor epoch override (si no se pasa, usa IngestionControl)",
        )
        parser.add_argument(
            "--show-samples",
            type=int,
            default=10,
            help="Cantidad de ejemplos a imprimir por categoria",
        )
        parser.add_argument(
            "--overlap-hours",
            type=int,
            default=None,
            help="Horas de solape para ventana incremental (default: setting EVOLUTION_SYNC_OVERLAP_HOURS)",
        )

    def handle(self, *args, **options):
        instance_name = str(options["instance"] or "").strip()
        page_size = max(1, int(options["page_size"] or 200))
        max_pages = max(1, int(options["max_pages"] or 10))
        since_epoch = options.get("since_epoch")
        show_samples = max(0, int(options["show_samples"] or 10))
        overlap_hours_opt = options.get("overlap_hours")

        try:
            instance = EvolutionInstance.objects.get(instance_name=instance_name)
        except EvolutionInstance.DoesNotExist:
            available = ", ".join(
                EvolutionInstance.objects.filter(is_active=True).values_list("instance_name", flat=True)
            )
            self.stdout.write(self.style.ERROR(
                f"Instancia '{instance_name}' no encontrada. Disponibles: {available or '(ninguna)'}"
            ))
            return

        control, _ = IngestionControl.objects.get_or_create(
            instance=instance,
            defaults={"last_sync_timestamp": datetime(1970, 1, 1, tzinfo=dt_timezone.utc)},
        )
        cursor_epoch = int(since_epoch) if since_epoch is not None else int(control.last_sync_timestamp.timestamp())
        overlap_hours = (
            max(0, int(overlap_hours_opt))
            if overlap_hours_opt is not None
            else max(0, int(getattr(settings, "EVOLUTION_SYNC_OVERLAP_HOURS", 6)))
        )
        effective_cursor_epoch = max(0, cursor_epoch - overlap_hours * 3600)
        cutoff_dt = datetime.fromtimestamp(effective_cursor_epoch, tz=dt_timezone.utc)

        service = IngestionService(instance_name=instance_name)

        self.stdout.write(self.style.WARNING(
            f"DRY-RUN iniciado | instancia={instance_name} | cursor_epoch={cursor_epoch} | overlap_hours={overlap_hours} | effective_cursor_epoch={effective_cursor_epoch} | page_size={page_size} | max_pages={max_pages}"
        ))

        all_records = []
        total_pages_hint = None

        for page in range(1, max_pages + 1):
            payload = service._fetch_messages_page(
                cursor_timestamp=effective_cursor_epoch,
                page=page,
                page_size=page_size,
            )
            records, current_page, pages_total = service._extract_page_bundle(payload)
            if total_pages_hint is None:
                total_pages_hint = pages_total

            if not records:
                break

            all_records.extend(records)
            self.stdout.write(
                f"Pagina {current_page}/{pages_total}: +{len(records)} (acumulado={len(all_records)})"
            )

            if current_page >= pages_total:
                break

        if not all_records:
            self.stdout.write(self.style.WARNING("No se recibieron registros para analizar."))
            return

        df = pd.DataFrame(all_records)
        if df.empty:
            self.stdout.write(self.style.WARNING("DataFrame vacio despues de parsear payload."))
            return

        df["external_id"] = df.apply(service._build_external_id, axis=1)
        df["wa_id"] = df.apply(service._extract_wa_id, axis=1)
        df["name"] = df.apply(service._extract_name, axis=1)
        df["phone_number"] = df.apply(service._extract_phone_number, axis=1)
        df["from_me"] = df.apply(service._extract_from_me, axis=1)
        df["chat_jid"] = df.apply(service._extract_chat_jid, axis=1)
        df["message_type"] = df.apply(service._extract_type, axis=1)
        df["timestamp"] = df.apply(service._extract_timestamp, axis=1)

        raw_total = len(df)
        df = df[df["external_id"].notna() & df["wa_id"].notna()].copy()
        valid_after_keys = len(df)
        before_cutoff = len(df)
        df = df[df["timestamp"] > cutoff_dt].copy()
        filtered_by_cutoff = before_cutoff - len(df)

        status_filtered = int(df["chat_jid"].astype(str).str.lower().eq("status@broadcast").sum())
        group_filtered = int(df["chat_jid"].astype(str).str.endswith("@g.us", na=False).sum())

        df = df[~df["chat_jid"].astype(str).str.lower().eq("status@broadcast")].copy()
        df = df[~df["chat_jid"].astype(str).str.endswith("@g.us", na=False)].copy()
        valid_after_chat_filters = len(df)

        if df.empty:
            self.stdout.write(self.style.WARNING("Sin filas validas luego de filtros."))
            return

        existing_ids = set(
            Message.objects.filter(external_id__in=df["external_id"].tolist()).values_list("external_id", flat=True)
        )
        df_new = df[~df["external_id"].isin(existing_ids)].copy()

        wa_ids = df["wa_id"].dropna().unique().tolist()
        user_by_wa = {u.wa_id: u for u in ChatUser.objects.filter(wa_id__in=wa_ids)}

        phone_numbers = [
            str(p).strip()
            for p in df["phone_number"].dropna().astype(str).unique().tolist()
            if str(p).strip()
        ]
        user_by_phone = {
            u.phone_number: u
            for u in ChatUser.objects.filter(phone_number__in=phone_numbers).exclude(phone_number="")
        }

        missing_wa_ids = [wa for wa in wa_ids if wa not in user_by_wa]
        would_create_users = 0
        would_link_by_phone = 0
        would_create_with_name = 0
        create_examples = []

        for wa_id in missing_wa_ids:
            subset = df[df["wa_id"] == wa_id]
            if subset.empty:
                continue

            first_row = subset.iloc[0]
            phone_number = str(first_row.get("phone_number") or "").strip()
            existing_user = user_by_phone.get(phone_number) if phone_number else None
            if existing_user:
                would_link_by_phone += 1
                user_by_wa[wa_id] = existing_user
                continue

            would_create_users += 1
            safe_name = service._pick_best_contact_name(subset)
            if safe_name:
                would_create_with_name += 1
            if len(create_examples) < show_samples:
                create_examples.append(
                    {
                        "wa_id": wa_id,
                        "phone": phone_number,
                        "suggested_name": safe_name or "",
                    }
                )

        # Simulacion de updates: misma regla de sync real
        wa_ids_by_user_id = {}
        for wa, user in user_by_wa.items():
            wa_ids_by_user_id.setdefault(user.id, set()).add(wa)

        would_update_last_interaction = 0
        would_fill_empty_name = 0
        protected_existing_name = 0
        fill_name_examples = []

        seen_user_ids = set()
        for wa_id, user in user_by_wa.items():
            if user.id in seen_user_ids:
                continue
            seen_user_ids.add(user.id)

            mapped_wa_ids = wa_ids_by_user_id.get(user.id) or {wa_id}
            subset = df[df["wa_id"].isin(list(mapped_wa_ids))]
            if subset.empty:
                continue

            newest_ts = subset["timestamp"].max()
            newest_name = service._pick_best_contact_name(subset)

            if newest_ts and newest_ts > user.last_interaction:
                would_update_last_interaction += 1

            current_name = str(user.name or "").strip()
            if newest_name and not current_name:
                would_fill_empty_name += 1
                if len(fill_name_examples) < show_samples:
                    fill_name_examples.append(
                        {
                            "user_id": user.id,
                            "wa_id": user.wa_id,
                            "new_name": newest_name,
                        }
                    )
            elif newest_name and current_name and newest_name != current_name:
                # Este caso NO se aplica por regla actual: no se sobreescribe nombre no vacio
                protected_existing_name += 1

        self.stdout.write("\n=== DRY-RUN RESUMEN ===")
        self.stdout.write(f"Registros crudos recibidos: {raw_total}")
        self.stdout.write(f"Validos (external_id + wa_id): {valid_after_keys}")
        self.stdout.write(f"Descartados por cutoff local ({cutoff_dt.isoformat()}): {filtered_by_cutoff}")
        self.stdout.write(f"Filtrados por status@broadcast: {status_filtered}")
        self.stdout.write(f"Filtrados por grupos (@g.us): {group_filtered}")
        self.stdout.write(f"Validos finales: {valid_after_chat_filters}")
        self.stdout.write(f"Mensajes nuevos (deduplicados contra external_id): {len(df_new)}")
        self.stdout.write(f"Mensajes duplicados detectados: {len(df) - len(df_new)}")

        self.stdout.write("\n=== USUARIOS (SIMULACION) ===")
        self.stdout.write(f"WA IDs en lote: {len(wa_ids)}")
        self.stdout.write(f"WA IDs faltantes (sin ChatUser directo): {len(missing_wa_ids)}")
        self.stdout.write(f"Se enlazarian por phone_number existente: {would_link_by_phone}")
        self.stdout.write(f"Se crearian usuarios nuevos: {would_create_users}")
        self.stdout.write(f"De los nuevos, con nombre sugerido no vacio: {would_create_with_name}")

        self.stdout.write("\n=== NOMBRES (REGLA ACTUAL) ===")
        self.stdout.write(f"Usuarios con last_interaction que se actualizaria: {would_update_last_interaction}")
        self.stdout.write(f"Usuarios con nombre vacio que se llenaria: {would_fill_empty_name}")
        self.stdout.write(f"Casos protegidos (nombre existente no se sobreescribe): {protected_existing_name}")

        if create_examples:
            self.stdout.write("\nEjemplos de usuarios que se crearian:")
            for row in create_examples:
                self.stdout.write(f"- wa_id={row['wa_id']} | phone={row['phone']} | suggested_name={row['suggested_name']}")

        if fill_name_examples:
            self.stdout.write("\nEjemplos de nombres que se llenarian (solo vacios):")
            for row in fill_name_examples:
                self.stdout.write(f"- user_id={row['user_id']} | wa_id={row['wa_id']} | new_name={row['new_name']}")

        self.stdout.write(self.style.SUCCESS("\nDRY-RUN completado: no se guardo ningun cambio en BD."))
