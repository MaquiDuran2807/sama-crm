"""Comando de seeding para crear datos demo del cliente solar Codensolar."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from crm.models import Contact, Lead
from ingesta.models import ChatUser, DailyTextSummary
from tenants.models import CustomField, PipelineConfig, Tenant, TenantModule


@dataclass(frozen=True)
class ContactSeed:
    """Estructura de datos para sembrar un contacto CRM."""

    full_name: str
    phone_number: str
    email: str
    address: str
    city: str
    utm_source: str
    utm_medium: str
    utm_campaign: str
    tipo_cliente: str
    consumo_kwh: int
    fecha_instalacion: str


@dataclass(frozen=True)
class LeadSeed:
    """Estructura de datos para sembrar un lead CRM."""

    contact_phone: str
    current_stage: str
    product_of_interest: str
    product_category: str
    notes: str
    is_closed: bool
    closed_result: str


class Command(BaseCommand):
    """Inserta un dataset inicial para un cliente solar de ejemplo."""

    help = "Crea tenant, pipeline, custom fields, contactos, leads y summaries para Codensolar SAS."

    def handle(self, *args: Any, **options: Any) -> None:
        """Ejecuta el proceso de seeding y muestra un resumen en consola."""

        with transaction.atomic():
            result = self._seed_data()

        self.stdout.write(self.style.SUCCESS("Seed completado: seed_solar_client"))
        self.stdout.write("- Tenant creado: {}".format(result["tenant_created"]))
        self.stdout.write("- Tenant actualizado: {}".format(result["tenant_updated"]))
        self.stdout.write("- Pipeline creado: {}".format(result["pipeline_created"]))
        self.stdout.write("- Pipeline actualizado: {}".format(result["pipeline_updated"]))
        self.stdout.write("- Modulos creados: {}".format(result["modules_created"]))
        self.stdout.write("- CustomFields creados: {}".format(result["custom_fields_created"]))
        self.stdout.write("- CustomFields existentes: {}".format(result["custom_fields_existing"]))
        self.stdout.write("- Contacts creados: {}".format(result["contacts_created"]))
        self.stdout.write("- Contacts existentes: {}".format(result["contacts_existing"]))
        self.stdout.write("- Leads creados: {}".format(result["leads_created"]))
        self.stdout.write("- Leads existentes: {}".format(result["leads_existing"]))
        self.stdout.write("- ChatUsers creados: {}".format(result["chat_users_created"]))
        self.stdout.write("- ChatUsers existentes: {}".format(result["chat_users_existing"]))
        self.stdout.write("- DailyTextSummary creados: {}".format(result["daily_summaries_created"]))
        self.stdout.write("- DailyTextSummary existentes: {}".format(result["daily_summaries_existing"]))

    def _seed_data(self) -> dict[str, int]:
        """Siembra todas las entidades requeridas y retorna metricas de resultado."""

        today = timezone.localdate()
        subscription_start = today - timedelta(days=10)
        subscription_end = subscription_start + timedelta(days=90)

        tenant, tenant_created = Tenant.objects.update_or_create(
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

        stages = [
            {"name": "Lead", "color": "#003366", "order": 1},
            {"name": "Calificacion", "color": "#FF9933", "order": 2},
            {"name": "Cotizacion Enviada", "color": "#FF6600", "order": 3},
            {"name": "Seguimiento", "color": "#FFCC00", "order": 4},
            {"name": "Cerrado Ganado", "color": "#00CC66", "order": 5},
            {"name": "Cerrado Perdido", "color": "#FF3333", "order": 6},
        ]
        _, pipeline_created = PipelineConfig.objects.update_or_create(
            tenant=tenant,
            defaults={"stages": stages, "allow_skip_stages": True},
        )

        custom_fields_created = 0
        custom_fields_existing = 0
        custom_fields_payload = [
            ("tipo_cliente", "select", ["residencial", "comercial", "industrial"], 1),
            ("consumo_kwh", "number", [], 2),
            ("fecha_instalacion", "date", [], 3),
        ]
        for field_name, field_type, options, order in custom_fields_payload:
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
                custom_fields_created += 1
            else:
                custom_fields_existing += 1

        contacts_created = 0
        contacts_existing = 0
        contacts_by_phone: dict[str, Contact] = {}
        for seed in self._contacts_seed():
            contact, created = Contact.objects.get_or_create(
                tenant=tenant,
                phone_number=seed.phone_number,
                defaults={
                    "full_name": seed.full_name,
                    "email": seed.email,
                    "address": seed.address,
                    "city": seed.city,
                    "utm_source": seed.utm_source,
                    "utm_medium": seed.utm_medium,
                    "utm_campaign": seed.utm_campaign,
                    "custom_fields": {
                        "tipo_cliente": seed.tipo_cliente,
                        "consumo_kwh": seed.consumo_kwh,
                        "fecha_instalacion": seed.fecha_instalacion,
                    },
                },
            )
            if created:
                contacts_created += 1
            else:
                contacts_existing += 1
            contacts_by_phone[seed.phone_number] = contact

        leads_created = 0
        leads_existing = 0
        for seed in self._leads_seed():
            contact = contacts_by_phone[seed.contact_phone]
            lead, created = Lead.objects.get_or_create(
                tenant=tenant,
                contact=contact,
                current_stage=seed.current_stage,
                notes=seed.notes,
                defaults={
                    "product_of_interest": seed.product_of_interest,
                    "product_category": seed.product_category,
                    "is_closed": seed.is_closed,
                    "closed_result": seed.closed_result,
                    "custom_fields": {
                        "seed_source": "seed_solar_client",
                    },
                    "skipped_stages": [],
                    "last_contacted_at": timezone.now(),
                },
            )
            if not created:
                lead.product_of_interest = seed.product_of_interest
                lead.product_category = seed.product_category
                lead.is_closed = seed.is_closed
                lead.closed_result = seed.closed_result
                lead.custom_fields = {"seed_source": "seed_solar_client"}
                lead.last_contacted_at = timezone.now()
                lead.save(
                    update_fields=[
                        "product_of_interest",
                        "product_category",
                        "is_closed",
                        "closed_result",
                        "custom_fields",
                        "last_contacted_at",
                        "updated_at",
                    ]
                )
            if created:
                leads_created += 1
            else:
                leads_existing += 1

        chat_users_created = 0
        chat_users_existing = 0
        daily_summaries_created = 0
        daily_summaries_existing = 0
        summary_contacts = list(self._contacts_seed()[:3])
        for index, seed in enumerate(summary_contacts):
            wa_id = seed.phone_number.replace("+", "")
            user, created = ChatUser.objects.get_or_create(
                wa_id=wa_id,
                defaults={
                    "name": seed.full_name,
                    "phone_number": seed.phone_number,
                    "is_customer": True,
                    "last_interaction": timezone.now(),
                },
            )
            if not created:
                user.name = seed.full_name
                user.phone_number = seed.phone_number
                user.is_customer = True
                user.last_interaction = timezone.now()
                user.save(update_fields=["name", "phone_number", "is_customer", "last_interaction"])

            summary_date = today - timedelta(days=index)
            _, summary_created = DailyTextSummary.objects.get_or_create(
                user=user,
                summary_date=summary_date,
                defaults={
                    "text": self._summary_text(seed.full_name, seed.city),
                    "has_data": True,
                    "pending_items": ["Enviar propuesta final", "Confirmar visita tecnica"],
                    "mentioned_people": ["Asesor Solar", "Instalador Senior"],
                    "deadlines": [
                        {
                            "item": "Seguimiento comercial",
                            "due_date": str(summary_date + timedelta(days=2)),
                        }
                    ],
                    "payment_promises": [],
                    "source_message_count": 5,
                    "source_last_message_ts": timezone.now(),
                    "prompt_tokens": 200,
                    "completion_tokens": 120,
                    "total_tokens": 320,
                },
            )
            if created:
                chat_users_created += 1
            else:
                chat_users_existing += 1
            if summary_created:
                daily_summaries_created += 1
            else:
                daily_summaries_existing += 1

        return {
            "tenant_created": int(tenant_created),
            "tenant_updated": int(not tenant_created),
            "pipeline_created": int(pipeline_created),
            "pipeline_updated": int(not pipeline_created),
            "modules_created": modules_created,
            "custom_fields_created": custom_fields_created,
            "custom_fields_existing": custom_fields_existing,
            "contacts_created": contacts_created,
            "contacts_existing": contacts_existing,
            "leads_created": leads_created,
            "leads_existing": leads_existing,
            "chat_users_created": chat_users_created,
            "chat_users_existing": chat_users_existing,
            "daily_summaries_created": daily_summaries_created,
            "daily_summaries_existing": daily_summaries_existing,
        }

    @staticmethod
    def _contacts_seed() -> tuple[ContactSeed, ...]:
        """Retorna los contactos de ejemplo para el cliente solar."""

        return (
            ContactSeed(
                full_name="Carolina Mejia",
                phone_number="+573001112233",
                email="carolina.mejia@correo.com",
                address="Cra 45 #12-33",
                city="Medellin",
                utm_source="google",
                utm_medium="cpc",
                utm_campaign="paneles-residencial-q2",
                tipo_cliente="residencial",
                consumo_kwh=420,
                fecha_instalacion="2026-08-15",
            ),
            ContactSeed(
                full_name="Andres Restrepo",
                phone_number="+573002223344",
                email="andres.restrepo@empresa.com",
                address="Cl 10 #22-19",
                city="Bogota",
                utm_source="meta",
                utm_medium="social",
                utm_campaign="energia-empresas",
                tipo_cliente="comercial",
                consumo_kwh=1180,
                fecha_instalacion="2026-09-01",
            ),
            ContactSeed(
                full_name="Maria Fernanda Rios",
                phone_number="+573003334455",
                email="maria.rios@hogar.net",
                address="Av 80 #44-70",
                city="Cali",
                utm_source="referral",
                utm_medium="word-of-mouth",
                utm_campaign="referidos-clientes",
                tipo_cliente="residencial",
                consumo_kwh=360,
                fecha_instalacion="2026-07-20",
            ),
            ContactSeed(
                full_name="Jorge Ivan Salazar",
                phone_number="+573004445566",
                email="jorge.salazar@industria.co",
                address="Zona Industrial Lote 9",
                city="Barranquilla",
                utm_source="web",
                utm_medium="organic",
                utm_campaign="landing-solar-industrial",
                tipo_cliente="industrial",
                consumo_kwh=3250,
                fecha_instalacion="2026-10-10",
            ),
            ContactSeed(
                full_name="Luisa Valentina Gomez",
                phone_number="+573005556677",
                email="luisa.gomez@startup.io",
                address="Cl 73 #8-44",
                city="Bogota",
                utm_source="tiktok",
                utm_medium="video",
                utm_campaign="energia-jovenes-emprendedores",
                tipo_cliente="comercial",
                consumo_kwh=760,
                fecha_instalacion="2026-08-30",
            ),
        )

    @staticmethod
    def _leads_seed() -> tuple[LeadSeed, ...]:
        """Retorna los leads demo distribuidos en etapas del pipeline."""

        return (
            LeadSeed(
                contact_phone="+573001112233",
                current_stage="Lead",
                product_of_interest="Kit Solar 3kW",
                product_category="Residencial",
                notes="[seed_solar_client] Primer contacto por formulario web.",
                is_closed=False,
                closed_result="",
            ),
            LeadSeed(
                contact_phone="+573002223344",
                current_stage="Calificacion",
                product_of_interest="Sistema On-Grid 10kW",
                product_category="Comercial",
                notes="[seed_solar_client] Validando consumo promedio trimestral.",
                is_closed=False,
                closed_result="",
            ),
            LeadSeed(
                contact_phone="+573003334455",
                current_stage="Cotizacion Enviada",
                product_of_interest="Kit Solar 4kW",
                product_category="Residencial",
                notes="[seed_solar_client] Cotizacion enviada por WhatsApp.",
                is_closed=False,
                closed_result="",
            ),
            LeadSeed(
                contact_phone="+573004445566",
                current_stage="Seguimiento",
                product_of_interest="Sistema Hibrido 20kW",
                product_category="Industrial",
                notes="[seed_solar_client] Pendiente visita tecnica en planta.",
                is_closed=False,
                closed_result="",
            ),
            LeadSeed(
                contact_phone="+573005556677",
                current_stage="Cerrado Ganado",
                product_of_interest="Sistema On-Grid 8kW",
                product_category="Comercial",
                notes="[seed_solar_client] Contrato firmado y anticipo recibido.",
                is_closed=True,
                closed_result="won",
            ),
            LeadSeed(
                contact_phone="+573001112233",
                current_stage="Cerrado Perdido",
                product_of_interest="Bateria de respaldo 5kWh",
                product_category="Residencial",
                notes="[seed_solar_client] Cliente aplazo proyecto por presupuesto.",
                is_closed=True,
                closed_result="lost",
            ),
            LeadSeed(
                contact_phone="+573002223344",
                current_stage="Seguimiento",
                product_of_interest="Mantenimiento preventivo anual",
                product_category="Comercial",
                notes="[seed_solar_client] Esperando aprobacion de compras.",
                is_closed=False,
                closed_result="",
            ),
            LeadSeed(
                contact_phone="+573003334455",
                current_stage="Lead",
                product_of_interest="Expansion paneles 2kW",
                product_category="Residencial",
                notes="[seed_solar_client] Consulta nueva por ampliacion.",
                is_closed=False,
                closed_result="",
            ),
        )

    @staticmethod
    def _summary_text(full_name: str, city: str) -> str:
        """Genera texto de resumen diario para un contacto."""

        return (
            f"Resumen IA: {full_name} en {city} solicito seguimiento comercial "
            "sobre instalacion solar y tiempos de implementacion."
        )
