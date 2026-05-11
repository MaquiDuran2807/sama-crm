"""Comando de seeding para generar datos de prueba realistas para Codensolar."""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from crm.models import City, Contact, Lead, LeadActivity, LeadSource, LeadTask, LeadTag, Tag, DailyFollowupReport, Department
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

        tags = self._crear_tags(tenant)

        self._asignar_tags_a_leads(leads, tags)

        self._crear_tareas(leads)

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
        """Genera 50 contactos con ciudades de la BD que tienen coordenadas."""
        from crm.models import City

        contacts = []

        all_cities = list(City.objects.filter(latitude__isnull=False, longitude__isnull=False))

        if not all_cities:
            dept, _ = Department.objects.get_or_create(name="Cundinamarca")
            fallback = [
                ("Bogotá", "Cundinamarca"),
                ("Cali", "Valle del Cauca"),
                ("Medellín", "Antioquia"),
                ("Barranquilla", "Atlántico"),
                ("Cartagena", "Bolívar"),
                ("Bucaramanga", "Santander"),
            ]
            for city_name, dept_name in fallback:
                d, _ = Department.objects.get_or_create(name=dept_name)
                c, _ = City.objects.get_or_create(department=d, name=city_name)
                all_cities.append(c)

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
            city = random.choice(all_cities)

            contact, created = Contact.objects.get_or_create(
                tenant=tenant,
                phone_number=telefono,
                defaults={
                    "full_name": nombre_completo,
                    "email": email,
                    "city": city,
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

            lead = Lead.objects.create(
                tenant=tenant,
                contact=contact,
                current_stage=stage,
                product_of_interest=random.choice(self.PRODUCTOS),
                product_category=random.choice(self.CATEGORIAS),
                notes=f"Lead generado automaticamente - Producto: {random.choice(self.PRODUCTOS)}",
                is_closed=is_closed,
                closed_result=closed_result,
                custom_fields={"source": "seed_solar_client"},
                skipped_stages=[],
                last_contacted_at=last_contacted,
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

    def _crear_tags(self, tenant: Tenant) -> list[Tag]:
        """Crea etiquetas predefinidas para el tenant."""
        tags_data = [
            {"name": "Prioridad Alta", "color": "#ef4444", "is_predefined": True},
            {"name": "Seguimiento", "color": "#f5a623", "is_predefined": True},
            {"name": "Nuevo Lead", "color": "#3b82f6", "is_predefined": True},
            {"name": "Caliente", "color": "#f06539", "is_predefined": True},
            {"name": "Frio", "color": "#64748b", "is_predefined": True},
            {"name": "VIP", "color": "#8b5cf6", "is_predefined": True},
            {"name": "Cotizacion Enviada", "color": "#2ec27e", "is_predefined": True},
            {"name": "Revisar", "color": "#ec4899", "is_predefined": True},
        ]

        tags = []
        for tag_data in tags_data:
            tag, created = Tag.objects.get_or_create(
                tenant=tenant,
                name=tag_data["name"],
                defaults={
                    "color": tag_data["color"],
                    "is_predefined": tag_data["is_predefined"],
                },
            )
            tags.append(tag)

        return tags

    def _asignar_tags_a_leads(self, leads: list[Lead], tags: list[Tag]) -> int:
        """Asigna etiquetas aleatorias a algunos leads."""
        assignments = 0
        for lead in leads:
            num_tags = random.randint(0, 3)
            if num_tags > 0:
                selected_tags = random.sample(tags, min(num_tags, len(tags)))
                for tag in selected_tags:
                    LeadTag.objects.get_or_create(
                        lead=lead,
                        tag=tag,
                    )
                    assignments += 1
        return assignments

    def _crear_tareas(self, leads: list[Lead]) -> int:
        """Crea tareas para algunos leads."""
        task_descriptions = [
            "Llamar al cliente para confirmar cita",
            "Enviar cotizacion por WhatsApp",
            "Realizar visita tecnica",
            "Confirmar disponibilidad de instalacion",
            "Revisar aprobacion de credito",
            "Seguimiento post-instalacion",
            "Enviar contrato firmado",
            "Confirmar fecha de entrega",
            "Actualizar informacion del lead",
            "Revisar requisitos para instalacion",
        ]

        tareas_creadas = 0
        leads_con_tareas = random.sample(leads, min(25, len(leads)))

        for lead in leads_con_tareas:
            num_tareas = random.randint(1, 3)
            for i in range(num_tareas):
                description = random.choice(task_descriptions)
                days_offset = random.randint(-5, 15)
                due_date = timezone.now() + timedelta(days=days_offset)

                is_completed = random.random() > 0.6

                LeadTask.objects.get_or_create(
                    lead=lead,
                    description=description,
                    defaults={
                        "due_date": due_date,
                        "is_completed": is_completed,
                        "completed_at": timezone.now() - timedelta(days=random.randint(1, 5)) if is_completed else None,
                    },
                )
                tareas_creadas += 1

        return tareas_creadas

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
            "tags": Tag.objects.filter(tenant=tenant).count(),
            "lead_tags": LeadTag.objects.filter(lead__tenant=tenant).count(),
            "tasks": LeadTask.objects.filter(lead__tenant=tenant).count(),
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
        self.stdout.write(f"{result['tags']} etiquetas creadas")
        self.stdout.write(f"{result['lead_tags']} etiquetas asignadas a leads")
        self.stdout.write(f"{result['tasks']} tareas creadas")

        stages_str = ", ".join([f"{k}: {v}" for k, v in result["stages_count"].items()])
        self.stdout.write(self.style.SUCCESS(f"Leads por etapa: {stages_str}"))