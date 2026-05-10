"""Serializadores REST de la app `crm`.

Transforma los modelos del dominio de contactos, leads, actividades y resenas
IA en payloads JSON listos para la API. Tambien encapsula reglas simples de
presentacion como la vista resumida del lead o el tiempo relativo de ultima
actualizacion.
"""

from rest_framework import serializers
from crm.domain.models import Contact, Lead, LeadSource, LeadActivity, LeadTask, Tag, LeadTag
from ingesta.models import DailyTextSummary


class LeadSourceSerializer(serializers.ModelSerializer):
    """Serializa la fuente de origen de un lead."""

    class Meta:
        model = LeadSource
        fields = ["platform", "utm_source", "utm_medium", "utm_campaign", "referrer_contact", "landing_page_url"]


class LeadActivitySerializer(serializers.ModelSerializer):
    """Serializa el historial de actividades asociado a un lead."""

    class Meta:
        model = LeadActivity
        fields = ["id", "activity_type", "description", "performed_by", "created_at"]


class LeadSerializer(serializers.ModelSerializer):
    """Serializer resumido para listado de leads.

    Expone campos de lectura rapida junto con datos derivados de `contact`,
    de manera que la capa de interfaces no tenga que encadenar relaciones de
    modelo en el frontend.
    """
    contact_name = serializers.CharField(source="contact.full_name", read_only=True)
    contact_phone = serializers.CharField(source="contact.phone_number", read_only=True)
    time_since_update = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    has_tasks = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            "id", "contact", "contact_name", "contact_phone",
            "current_stage", "product_of_interest", "product_category",
            "is_closed", "closed_result",
            "created_at", "updated_at", "last_contacted_at", "time_since_update",
            "tags", "has_tasks",
        ]

    def get_time_since_update(self, obj):
        """Devuelve una representacion humana del tiempo desde la ultima edicion."""

        from django.utils import timezone
        from datetime import timedelta
        now = timezone.now()
        delta = now - obj.updated_at
        if delta < timedelta(hours=1):
            return f"hace {delta.seconds // 60} min"
        elif delta < timedelta(days=1):
            return f"hace {delta.seconds // 3600}h"
        return f"hace {delta.days} días"

    def get_tags(self, obj):
        """Devuelve lista de {name, color} de las etiquetas del lead."""
        return [
            {"id": lt.tag.id, "name": lt.tag.name, "color": lt.tag.color}
            for lt in obj.lead_tags.select_related("tag").all()
        ]

    def get_has_tasks(self, obj):
        """Devuelve True si el lead tiene tareas no completadas."""
        return obj.tasks.filter(is_completed=False).exists()


class LeadDetailSerializer(serializers.ModelSerializer):
    """Serializer completo para el detalle de un lead."""
    contact = serializers.SerializerMethodField()
    source = LeadSourceSerializer(read_only=True)
    activities = LeadActivitySerializer(many=True, read_only=True)
    tenant = serializers.PrimaryKeyRelatedField(read_only=True)
    tags = serializers.SerializerMethodField()
    tasks = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            "id", "tenant", "contact", "current_stage",
            "product_of_interest", "product_category", "notes",
            "skipped_stages", "is_closed", "closed_result",
            "custom_fields", "source", "activities",
            "created_at", "updated_at", "last_contacted_at",
            "tags", "tasks",
        ]

    def get_contact(self, obj):
        """Construye el fragmento de contacto que consume la vista detalle."""

        return {
            "id": obj.contact.id,
            "full_name": obj.contact.full_name,
            "phone_number": obj.contact.phone_number,
            "email": obj.contact.email,
        }

    def get_tags(self, obj):
        """Devuelve lista de {id, name, color} de las etiquetas del lead."""
        return [
            {"id": lt.tag.id, "name": lt.tag.name, "color": lt.tag.color}
            for lt in obj.lead_tags.select_related("tag").all()
        ]

    def get_tasks(self, obj):
        """Devuelve lista de tareas del lead ordenadas por creacion."""
        from crm.interfaces.serializers import TaskSerializer
        return TaskSerializer(obj.tasks.all().order_by("-created_at"), many=True).data


class LeadCreateSerializer(serializers.ModelSerializer):
    """Serializer de escritura para crear leads desde la API."""
    class Meta:
        model = Lead
        fields = [
            "contact", "current_stage", "product_of_interest",
            "product_category", "notes", "custom_fields",
        ]


class ContactSerializer(serializers.ModelSerializer):
    """Serializer para listar y editar contactos CRM."""

    last_lead = serializers.SerializerMethodField()
    city_name = serializers.CharField(source="city.name", read_only=True, allow_null=True)
    department_name = serializers.CharField(source="city.department.name", read_only=True, allow_null=True)

    class Meta:
        model = Contact
        fields = [
            "id", "tenant", "full_name", "phone_number", "email",
            "address", "city", "city_name", "department_name", "region",
            "utm_source", "utm_medium", "utm_campaign",
            "referrer_contact", "custom_fields", "last_lead", "created_at", "updated_at",
        ]
        read_only_fields = ["tenant"]

    def get_last_lead(self, obj):
        """Recupera el ultimo lead del contacto para mostrar contexto comercial."""

        last = obj.leads.order_by("-created_at").first()
        if last:
            return {
                "id": last.id,
                "current_stage": last.current_stage,
                "product_of_interest": last.product_of_interest,
            }
        return None


class LeadSummarySerializer(serializers.ModelSerializer):
    """Serializer de salida para el resumen diario generado por IA."""
    class Meta:
        model = DailyTextSummary
        fields = [
            "id", "summary_date", "text",
            "pending_items", "mentioned_people", "deadlines", "payment_promises",
        ]


class LeadsStatsSerializer(serializers.Serializer):
    """Serializer para las metricas agregadas del pipeline."""
    total_leads = serializers.IntegerField()
    leads_nuevos_hoy = serializers.IntegerField()
    leads_por_etapa = serializers.DictField(child=serializers.IntegerField())
    active_leads = serializers.IntegerField()
    won_leads = serializers.IntegerField()


class TagSerializer(serializers.ModelSerializer):
    """Serializer para etiquetas de leads."""

    class Meta:
        model = Tag
        fields = ["id", "name", "color", "is_predefined", "created_at"]
        read_only_fields = ["id", "created_at"]


class LeadTagSerializer(serializers.ModelSerializer):
    """Serializer para relaciones LeadTag."""
    tag_name = serializers.CharField(source="tag.name", read_only=True)
    tag_color = serializers.CharField(source="tag.color", read_only=True)
    tag_id = serializers.IntegerField(source="tag.id", read_only=True)

    class Meta:
        model = LeadTag
        fields = ["id", "tag_id", "tag_name", "tag_color", "created_at"]


class TaskSerializer(serializers.ModelSerializer):
    """Serializer para tareas de leads."""

    class Meta:
        model = LeadTask
        fields = ["id", "description", "due_date", "is_completed", "completed_at", "created_at"]
        read_only_fields = ["id", "completed_at", "created_at"]