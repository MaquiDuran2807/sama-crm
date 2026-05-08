from django.contrib import admin
from django.db.models import Q
from django.utils.safestring import mark_safe

from .models import (ChatUser, DailyTextSummary, EvolutionInstance,
					 IngestionControl, Message, MonthlyTextSummary,
                     SummaryExecutionControl)
from .models import UserInteraction


class MessageMediaStateFilter(admin.SimpleListFilter):
	title = "estado media"
	parameter_name = "media_state"

	def lookups(self, request, model_admin):
		return (
			("available", "Media disponible"),
			("encrypted", "Media cifrada (.enc)"),
			("no_media", "Media faltante (NO_MEDIA)"),
			("non_media", "No es mensaje media"),
		)

	def queryset(self, request, queryset):
		value = self.value()
		media_types = [Message.MessageType.AUDIO, Message.MessageType.IMAGE, Message.MessageType.VIDEO]
		if value == "available":
			return queryset.filter(message_type__in=media_types).exclude(media_file="").exclude(media_file__isnull=True).exclude(media_file__iendswith=".enc")
		if value == "encrypted":
			return queryset.filter(message_type__in=media_types, media_file__iendswith=".enc")
		if value == "no_media":
			return queryset.filter(message_type__in=media_types).filter(Q(media_file="") | Q(media_file__isnull=True))
		if value == "non_media":
			return queryset.exclude(message_type__in=media_types)
		return queryset


@admin.register(EvolutionInstance)
class EvolutionInstanceAdmin(admin.ModelAdmin):
	list_display = ("instance_name", "description", "is_active", "created_at")
	search_fields = ("instance_name", "description")
	list_filter = ("is_active", "created_at")
	readonly_fields = ("created_at", "updated_at")


@admin.register(ChatUser)
class ChatUserAdmin(admin.ModelAdmin):
	list_display = ("name", "phone_number", "wa_id", "is_customer", "last_interaction")
	search_fields = ("wa_id", "phone_number", "name")
	list_filter = ("is_customer", "last_interaction")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
	list_display = (
		"external_id",
		"media_state_badge",
		"direction",
		"user",
		"message_type",
		"media_preview",
		"timestamp",
		"processed",
	)
	list_filter = ("direction", "from_me", "message_type", MessageMediaStateFilter, "user", "processed", "timestamp")
	search_fields = (
		"external_id",
		"chat_jid",
		"sender_wa_id",
		"recipient_wa_id",
		"quoted_external_id",
		"user__wa_id",
		"user__phone_number",
		"user__name",
		"content",
		"media_url",
	)
	autocomplete_fields = ("user",)
	readonly_fields = ("raw_data", "media_preview")
	list_select_related = ("user",)
	date_hierarchy = "timestamp"

	@admin.display(description="Estado media")
	def media_state_badge(self, obj):
		state = obj.media_state
		if state == "AVAILABLE":
			return mark_safe('<span style="padding:2px 8px;border-radius:999px;background:#dcfce7;color:#166534;font-weight:700;">AVAILABLE</span>')
		if state == "ENCRYPTED_FILE":
			return mark_safe('<span style="padding:2px 8px;border-radius:999px;background:#fef3c7;color:#92400e;font-weight:700;">ENCRYPTED</span>')
		if state == "NO_MEDIA":
			return mark_safe('<span style="padding:2px 8px;border-radius:999px;background:#fee2e2;color:#991b1b;font-weight:700;">NO_MEDIA</span>')
		return mark_safe('<span style="padding:2px 8px;border-radius:999px;background:#e5e7eb;color:#374151;font-weight:700;">NON_MEDIA</span>')

	@admin.display(description="Media")
	def media_preview(self, obj):
		if obj.message_type not in {Message.MessageType.AUDIO, Message.MessageType.IMAGE, Message.MessageType.VIDEO}:
			return "-"

		links = []
		is_encrypted_origin = bool(obj.media_url and obj.media_url.lower().split("?", 1)[0].endswith(".enc"))
		if obj.media_file:
			links.append(f'<a href="{obj.media_file.url}" target="_blank">Archivo</a>')
		if obj.media_url:
			links.append(f'<a href="{obj.media_url}" target="_blank">Origen</a>')

		preview_src = obj.media_file.url if obj.media_file else (obj.media_url if obj.media_url and not is_encrypted_origin else "")
		if preview_src:
			if obj.message_type == Message.MessageType.AUDIO:
				links.append(f'<audio controls src="{preview_src}" style="height: 28px; max-width: 260px;"></audio>')
			elif obj.message_type == Message.MessageType.IMAGE:
				links.append(f'<img src="{preview_src}" style="max-height: 90px; max-width: 180px; border-radius: 6px;" />')
			elif obj.message_type == Message.MessageType.VIDEO:
				links.append(f'<video controls src="{preview_src}" style="max-height: 90px; max-width: 180px; border-radius: 6px;"></video>')
		elif is_encrypted_origin:
			links.append("Origen cifrado (.enc): requiere endpoint de descarga/descifrado de Evolution para previsualizar.")

		if not links:
			return "Sin media"
		return mark_safe("<br>".join(links))


@admin.register(IngestionControl)
class IngestionControlAdmin(admin.ModelAdmin):
	list_display = ("instance", "last_sync_timestamp")
	search_fields = ("instance__instance_name",)
	list_select_related = ("instance",)


@admin.register(SummaryExecutionControl)
class SummaryExecutionControlAdmin(admin.ModelAdmin):
	list_display = (
		"run_key",
		"slot_start",
		"slot_end",
		"status",
		"eligible_users",
		"processed_users",
		"failed_users",
		"total_tokens",
	)
	list_filter = ("status", "slot_start", "slot_end")
	search_fields = ("run_key", "detail")
	readonly_fields = ("meta",)


@admin.register(DailyTextSummary)
class DailyTextSummaryAdmin(admin.ModelAdmin):
	list_display = (
		"summary_date",
		"user",
		"has_data",
		"source_message_count",
		"total_tokens",
		"updated_at",
	)
	list_filter = ("summary_date", "has_data")
	search_fields = ("user__name", "user__phone_number", "user__wa_id", "text")
	autocomplete_fields = ("user",)
	readonly_fields = ("created_at", "updated_at")


@admin.register(MonthlyTextSummary)
class MonthlyTextSummaryAdmin(admin.ModelAdmin):
	list_display = (
		"year",
		"month",
		"revision",
		"is_current",
		"user",
		"has_data",
		"source_message_count",
		"total_tokens",
	)
	list_filter = ("year", "month", "is_current", "has_data")
	search_fields = ("user__name", "user__phone_number", "user__wa_id", "text")
	autocomplete_fields = ("user",)


@admin.register(UserInteraction)
class UserInteractionAdmin(admin.ModelAdmin):
	list_display = (
		"occurred_at",
		"user",
		"interaction_type",
		"direction",
		"from_me",
		"duration_seconds",
		"is_video",
		"source",
	)
	list_filter = ("interaction_type", "direction", "from_me", "is_video", "source", "occurred_at")
	search_fields = ("user__name", "user__phone_number", "user__wa_id", "source_ref", "content")
	autocomplete_fields = ("user",)
