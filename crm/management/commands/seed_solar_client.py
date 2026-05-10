"""Comando de seeding para generar datos de prueba realistas para Codensolar."""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from crm.models import Contact, Lead, LeadActivity, LeadSource, DailyFollowupReport
from tenants.models import CustomField, PipelineConfig, Tenant, TenantModule


class Command(BaseCommand):
    """Genera datos de prueba realistas para el tenant Codensolar SAS."""

    help = "Crea 50 contactos, 100+ leads con fuentes y reportes de seguimiento para Codensolar."

    # Semilla para reproducibilidad
    SEED = 42

    # Nombres femeninos colombianos
    NOMBRES_FEMENINOS = [
        "Carolina", "Maria", "Laura", "Sofia", "Valentina", "Isabella", "Mariana", "Camila",
        "Daniela", "Gabriela", "Natalia", "Andrea", "Paula", " Cristina", "Luisa", "Fernanda",
        "Esperanza", "Catalina", "Juana", "Rosa"
    ]

    # Nombres masculinos colombianos
    NOMBRES_MASCULINOS = [
        "Juan", "Carlos", "Luis", "Andres", "Diego", "Javier", "Mauricio", "Alejandro",
        "David", "Fernando", "Gabriel", "Sebastian", "Miguel", "Ricardo", "Oscar", "Pedro",
        "Daniel", "Eduardo", "Jorge", "Santiago"
    ]

    # Apellidos colombianos
    APELLIDOS = [
        "Garcia", "Rodriguez", "Martinez", "Lopez", "Gonzalez", "Perez", "Sanchez", "Ramirez",
        "Torres", "Flores", "Rivera", "Gomez", "Diaz", "Cruz", "Reyes"
    ]

    # Ciudades colombianas
    CIUDADES = [
        "Bogota", "Medellin", "Cali", "Barranquilla", "Cartagena", "Bucaramanga",
        "Cundinamarca", "Antioquia"
    ]

    # Productos de energia solar
    PRODUCTOS = [
        "Panel Solar 450W",
        "Panel Solar 550W",
        "Inversor On-Grid 3kW",
        "Inversor Hibrido 5kW",
        "Inversor Off-Grid 2kW",
        "Bateria Litio 5kWh",
        "Bateria Litio 10kWh",
        "Bateria de Gel 200Ah",
        "Kit Solar Hogar 3kW",
        "Kit Solar Comercial 10kW",
        "Sistema de Monitoreo WiFi",
        "Estructura de Montaje para Techo"
    ]

    # Categorias de productos
    CATEGORIAS = ["Residencial", "Comercial", "Industrial"]

    # Plataformas para LeadSource
    PLATAFORMAS = ["meta", "google", "tiktok", "web", "referral"]

    # Fuentes UTM
    UTM_SOURCES = ["facebook_ads", "google_ads", "tiktok_ads", "organic", "newsletter", "referral_program"]

    # Medios UTM
    UTM_MEDIUMS = ["cpc", "social", "email", "organic"]

    # Campanas UTM
    UTM_CAMPANAS = [
        "campaign_verano_2026", "promo_baterias", "lanzamiento_kit", "descuento_panel",
        "oferta_inversor", "promo_mes", "black_friday", "energy_day", "campana_residencial",
        "campana_comercial", "webinar_solar", "feria_energia"
    ]

    # URLs de landing pages
    LANDING_PAGES = [
        "/productos/paneles", "/productos/inversores", "/productos/baterias",
        "/promociones/kit-solar", "/promociones/ofertas", "/contacto", "/blog/energia-solar",
        "/calculadora", "/servicios/instalacion", "/nosotros"
    ]

    def handle(self, *args: Any, **options: Any) -> None:
        """Ejecuta el proceso de seeding con datos reproducibles."""
        random.seed(self.SEED)

        with transaction.atomic():
            result = self._seed_data()

        self._mostrar_resumen(result)

    def _seed_data(self) -> dict[str, Any]:
        """Siembra todos los datos y retorna metricas."""
        tenant = self._crear_tenant()

        self._crear_pipeline(tenant)
        self._crear_modulos(tenant)
        self._crear_custom_fields(tenant)

        contacts = self._crear_contactos(tenant)

        leads = self._crear_leads(tenant, contacts)

        self._crear_lead_sources(leads)

        self._crear_actividades(leads)

        self._crear_reportes_seguimiento(tenant, leads)

        return self._obtener_counts(tenant)

    def _crear_tenant(self) -> Tenant:
        """Crea o actualiza el tenant Codensolar."""
        today = timezone.localdate()
        subscription_start = today - timedelta(days=180)
        subscription_end = subscription_start + timedelta(days=365)

        tenant, created = Tenant.objects.update_or_create(
            slug="codensolar",
            defaults={
                "name": "Codensolar SAS",
                "is_active": True,
                "tier": "pro",
                "period": "quarterly",
                "subscription_start": subscription_start,
                "subscription_end": subscription_end,
                "auto_renew": True,
                "blueprint": {
                    "industry": "solar",
                    "currency": "COP",
                    "language": "es-CO",
                },
            },
        )
        return tenant

    def _crear_pipeline(self, tenant: Tenant) -> None:
        """Crea el pipeline de ventas."""
        stages = [
            {"name": "Lead", "color": "#003366", "order": 1},
            {"name": "Calificacion", "color": "#FF9933", "order": 2},
            {"name": "Cotizacion Enviada", "color": "#FF6600", "order": 3},
            {"name": "Seguimiento", "color": "#FFCC00", "order": 4},
            {"name": "Cerrado Ganado", "color": "#00CC66", "order": 5},
            {"name": "Cerrado Perdido", "color": "#FF3333", "order": 6},
        ]
        PipelineConfig.objects.update_or_create(
            tenant=tenant,
            defaults={"stages": stages, "allow_skip_stages": True},
        )

    def _crear_modulos(self, tenant: Tenant) -> int:
        """Crea los modulos activos del tenant."""
        modules_created = 0
        for module_key, display_name in (
            ("crm", "CRM"),
            ("ingesta", "Ingesta"),
            ("analytics", "Analitica Comercial"),
        ):
            _, created = TenantModule.objects.get_or_create(
                tenant=tenant,
                module_key=module_key,
                defaults={"display_name": display_name, "is_active": True, "config": {}},
            )
            if created:
                modules_created += 1
        return modules_created

    def _crear_custom_fields(self, tenant: Tenant) -> int:
        """Crea los campos personalizados."""
        fields_data = [
            ("tipo_cliente", "select", ["residencial", "comercial", "industrial"], 1),
            ("consumo_kwh", "number", [], 2),
            ("fecha_instalacion", "date", [], 3),
            ("presupuesto", "number", [], 4),
            ("tipo_techo", "select", ["teja", "losa", "metalico", "otro"], 5),
        ]
        fields_created = 0
        for field_name, field_type, options, order in fields_data:
            _, created = CustomField.objects.get_or_create(
                tenant=tenant,
                target_model=CustomField.TargetModel.CONTACT,
                field_name=field_name,
                defaults={
                    "field_type": field_type,
                    "options": options,
                    "is_required": False,
                    "order": order,
                },
            )
            if created:
                fields_created += 1
        return fields_created

    def _crear_contactos(self, tenant: Tenant) -> list[Contact]:
        """Genera 50 contactos con nombres realistas."""
        contacts = []

        generos = ["F"] * 25 + ["M"] * 25

        for i in range(50):
            genero = random.choice(generos)
            if genero == "F":
                nombre = random.choice(self.NOMBRES_FEMENINOS)
            else:
                nombre = random.choice(self.NOMBRES_MASCULINOS)

            apellido = random.choice(self.APELLIDOS)
            nombre_completo = f"{nombre} {apellido}"
            email = f"{nombre.lower()}.{apellido.lower()}{i}@example.com"
            telefono = f"+57 300 {random.randint(100, 999)} {random.randint(1000, 9999)}"
            ciudad = random.choice(self.CIUDADES)

            contact, created = Contact.objects.get_or_create(
                tenant=tenant,
                phone_number=telefono,
                defaults={
                    "full_name": nombre_completo,
                    "email": email,
                    "city": ciudad,
                    "utm_source": random.choice(self.UTM_SOURCES),
                    "utm_medium": random.choice(self.UTM_MEDIUMS),
                    "utm_campaign": random.choice(self.UTM_CAMPANAS),
                    "custom_fields": {
                        "tipo_cliente": random.choice(["residencial", "comercial", "industrial"]),
                        "consumo_kwh": random.randint(200, 5000),
                    },
                },
            )
            contacts.append(contact)

        return contacts

    def _crear_leads(self, tenant: Tenant, contacts: list[Contact]) -> list[Lead]:
        """Genera 100+ leads distribuidos entre los contactos."""
        stages = ["Lead", "Calificacion", "Cotizacion Enviada", "Seguimiento", "Cerrado Ganado", "Cerrado Perdido"]
        leads = []

        today = date.today()
        start_date = date(2026, 1, 1)

        for i in range(110):
            contact = random.choice(contacts)
            stage = random.choice(stages)

            dias_offset = random.randint(0, (today - start_date).days)
            created_at = datetime.combine(start_date + timedelta(days=dias_offset), time(9, 0))
            created_at = timezone.make_aware(created_at, timezone.get_current_timezone())

            updated_at = created_at + timedelta(hours=random.randint(1, 48))

            is_closed = stage in ["Cerrado Ganado", "Cerrado Perdido"]
            closed_result = "won" if stage == "Cerrado Ganado" else ("lost" if stage == "Cerrado Perdido" else "")

            last_contacted = None
            if random.random() > 0.3:
                last_contacted = created_at + timedelta(days=random.randint(1, 30))

            lead, _ = Lead.objects.get_or_create(
                tenant=tenant,
                contact=contact,
                current_stage=stage,
                defaults={
                    "product_of_interest": random.choice(self.PRODUCTOS),
                    "product_category": random.choice(self.CATEGORIAS),
                    "notes": f"Lead generado automaticamente - Producto: {random.choice(self.PRODUCTOS)}",
                    "is_closed": is_closed,
                    "closed_result": closed_result,
                    "custom_fields": {"source": "seed_solar_client"},
                    "skipped_stages": [],
                    "last_contacted_at": last_contacted,
                },
            )

            Lead.objects.filter(pk=lead.pk).update(
                created_at=created_at,
                updated_at=updated_at,
                last_contacted_at=last_contacted,
            )
            lead.refresh_from_db()
            leads.append(lead)

        return leads

    def _crear_lead_sources(self, leads: list[Lead]) -> int:
        """Crea LeadSource para cada lead con datos aleatorios."""
        sources_created = 0

        for lead in leads:
            LeadSource.objects.get_or_create(
                lead=lead,
                defaults={
                    "platform": random.choice(self.PLATAFORMAS),
                    "utm_source": random.choice(self.UTM_SOURCES),
                    "utm_medium": random.choice(self.UTM_MEDIUMS),
                    "utm_campaign": random.choice(self.UTM_CAMPANAS),
                    "landing_page_url": random.choice(self.LANDING_PAGES),
                },
            )
            sources_created += 1

        return sources_created

    def _crear_actividades(self, leads: list[Lead]) -> int:
        """Crea actividades para los leads."""
        actividades_creadas = 0

        for lead in leads:
            num_actividades = random.randint(1, 3)
            for i in range(num_actividades):
                LeadActivity.objects.get_or_create(
                    lead=lead,
                    activity_type=random.choice(["lead_created", "note_added", "stage_change"]),
                    defaults={
                        "description": f"Actividad automatica: {random.choice(['Nota adicionada', 'Cambio de etapa', 'Seguimiento realizado'])}",
                        "performed_by": "seed_solar_client",
                    },
                )
                actividades_creadas += 1

        return actividades_creadas

    def _crear_reportes_seguimiento(self, tenant: Tenant, leads: list[Lead]) -> int:
        """Crea 3 reportes de seguimiento con leads frios."""
        cold_leads = [l for l in leads if l.current_stage in ["Lead", "Calificacion"]]
        if len(cold_leads) < 3:
            cold_leads = leads[:3]

        reportes = [
            (DailyFollowupReport.ReportType.MANANA, date(2026, 5, 1), cold_leads[:2]),
            (DailyFollowupReport.ReportType.TARDE, date(2026, 5, 1), cold_leads[2:3]),
            (DailyFollowupReport.ReportType.MANANA, date(2026, 5, 8), cold_leads[:2]),
        ]

        for report_type, report_date, target_leads in reportes:
            lead_ids = [l.pk for l in target_leads]
            DailyFollowupReport.objects.get_or_create(
                tenant=tenant,
                report_type=report_type,
                date=report_date,
                defaults={
                    "target_leads": lead_ids,
                    "summary": f"Reporte de seguimiento generado automaticamente para {len(lead_ids)} leads.",
                },
            )

        return len(reportes)

    def _obtener_counts(self, tenant: Tenant) -> dict[str, Any]:
        """Obtiene el conteo final de todos los elementos creados."""
        leads_qs = Lead.objects.filter(tenant=tenant)

        stages_count = {}
        for stage in ["Lead", "Calificacion", "Cotizacion Enviada", "Seguimiento", "Cerrado Ganado", "Cerrado Perdido"]:
            stages_count[stage] = leads_qs.filter(current_stage=stage).count()

        return {
            "contacts": Contact.objects.filter(tenant=tenant).count(),
            "leads": Lead.all_objects.filter(tenant=tenant).count(),
            "lead_sources": LeadSource.objects.filter(lead__tenant=tenant).count(),
            "lead_activities": LeadActivity.objects.filter(lead__tenant=tenant).count(),
            "reports": DailyFollowupReport.objects.filter(tenant=tenant).count(),
            "stages_count": stages_count,
        }

    def _mostrar_resumen(self, result: dict[str, Any]) -> None:
        """Imprime el resumen final del seeding."""
        self.stdout.write(self.style.SUCCESS("Seed completado: seed_solar_client"))
        self.stdout.write(f"{result['contacts']} contactos creados")
        self.stdout.write(f"{result['leads']} leads creados")
        self.stdout.write(f"{result['lead_sources']} LeadSource creados")
        self.stdout.write(f"{result['lead_activities']} actividades creadas")
        self.stdout.write(f"{result['reports']} reportes de seguimiento creados")

        stages_str = ", ".join([f"{k}: {v}" for k, v in result["stages_count"].items()])
        self.stdout.write(self.style.SUCCESS(f"Leads por etapa: {stages_str}"))