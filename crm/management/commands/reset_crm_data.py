"""Comando de gestión para eliminar datos de CRM."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from crm.models import Contact, Lead, LeadActivity, LeadSource


class Command(BaseCommand):
    """Elimina los datos de CRM (leads, contactos, actividades) manteniendo el tenant."""

    help = "Elimina leads, contactos y actividades de CRM. El tenant se mantiene."

    def add_arguments(self, parser: Any) -> None:
        """Agrega argumentos opcionales al comando."""
        parser.add_argument(
            "--confirmar",
            action="store_true",
            help="Omite la confirmación interactiva (para scripts/automación).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Ejecuta la eliminación de datos con confirmación del usuario."""
        confirmar = options.get("confirmar", False)

        if not confirmar:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️ Esto eliminará TODOS los leads, contactos y actividades de CRM. ¿Estás seguro? (sí/no)"
                )
            )
            respuesta = input().strip().lower()
            if respuesta != "sí":
                self.stdout.write(self.style.WARNING("Operación cancelada."))
                return

        with transaction.atomic():
            counts = self._eliminar_datos()

        self._mostrar_resumen(counts)

    def _eliminar_datos(self) -> dict[str, int]:
        """Elimina los datos de CRM en el orden correcto para respetar claves foráneas."""
        counts: dict[str, int] = {}

        counts["lead_activities"] = LeadActivity.objects.count()
        LeadActivity.objects.all().delete()

        counts["lead_sources"] = LeadSource.objects.count()
        LeadSource.objects.all().delete()

        counts["leads"] = Lead.all_objects.count()
        Lead.all_objects.all().delete()

        counts["contacts"] = Contact.objects.count()
        Contact.objects.all().delete()

        return counts

    def _mostrar_resumen(self, counts: dict[str, int]) -> None:
        """Muestra el resumen de eliminación en consola."""
        parts = []
        for key, count in counts.items():
            if count > 0:
                parts.append(f"{count} {key}")

        if not parts:
            self.stdout.write(self.style.SUCCESS("✅ No había datos para eliminar."))
            return

        mensaje = "✅ Datos eliminados: " + ", ".join(parts)
        self.stdout.write(self.style.SUCCESS(mensaje))