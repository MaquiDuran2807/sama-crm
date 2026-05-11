"""Carga coordenadas de ciudades desde el CSV estatico hacia la BD.

Uso:
    python manage.py seed_city_coords

Este comando lee `crm/static/crm/data/ciudades_colombia.csv` y actualiza el campo
`latitude` y `longitude` de cada City en la base de datos que coincida por nombre.
Si la ciudad no existe, la crea dentro del departamento correspondiente.
"""

from __future__ import annotations

import csv
import unicodedata
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand

from crm.models import City, Department


class Command(BaseCommand):
    """Carga coordenadas de ciudades colombianas desde el CSV a la BD."""

    help = "Carga coordenadas de ciudades desde el CSV estatico a la tabla City de la BD."

    def _normalize(self, name: str) -> str:
        """Normaliza un nombre de ciudad para hacer matching aproximado."""
        normalized = unicodedata.normalize("NFD", name.strip())
        normalized = normalized.translate({c: "" for c in range(0x0300, 0x0370)})
        return normalized.lower()

    def _find_or_create_department(self, dept_name: str) -> Department:
        """Busca o crea un departamento."""
        dept, _ = Department.objects.get_or_create(name=dept_name)
        return dept

    def handle(self, *args: Any, **options: Any) -> None:
        csv_path = (
            Path(__file__).resolve().parent.parent.parent
            / "static" / "crm" / "data" / "ciudades_colombia.csv"
        )

        if not csv_path.exists():
            self.stderr.write(f"CSV no encontrado en: {csv_path}")
            return

        updated = 0
        created = 0

        all_cities = {self._normalize(c.name): c for c in City.objects.all()}
        all_depts = {d.name.lower(): d for d in Department.objects.all()}

        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                city_name = row["nombre"].strip()
                dept_name = row.get("departamento", "").strip()
                lat = float(row["latitud"])
                lng = float(row["longitud"])

                key = self._normalize(city_name)

                existing = all_cities.get(key)
                if existing:
                    existing.latitude = lat
                    existing.longitude = lng
                    existing.save(update_fields=["latitude", "longitude"])
                    updated += 1
                    self.stdout.write(f"  Actualizado: {existing.name} ({lat}, {lng})")
                else:
                    dept = self._find_or_create_department(dept_name)
                    City.objects.create(
                        department=dept,
                        name=city_name,
                        latitude=lat,
                        longitude=lng,
                    )
                    created += 1
                    self.stdout.write(f"  Creado: {city_name} ({lat}, {lng})")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nCoordenadas cargadas: {updated} actualizadas, {created} creadas"
            )
        )
