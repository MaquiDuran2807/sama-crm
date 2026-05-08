from django.db import models
from django.utils import timezone


class EvolutionInstance(models.Model):
	"""Almacena instancias de Evolution API para multi-tenant support."""
	instance_name = models.CharField(max_length=120, unique=True)
	description = models.CharField(max_length=255, blank=True)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["instance_name"]

	def __str__(self):
		return f"{self.instance_name} {'✓' if self.is_active else '✗'}"


class ChatUser(models.Model):
	wa_id = models.CharField(max_length=64, unique=True)
	name = models.CharField(max_length=255, blank=True)
	phone_number = models.CharField(max_length=32, blank=True, default="", db_index=True)
	is_customer = models.BooleanField(default=True, db_index=True)
	last_interaction = models.DateTimeField(default=timezone.now)

	def display_label(self):
		label = self.name.strip() or self.phone_number.strip() or self.wa_id
		if self.phone_number and self.phone_number != label:
			return f"{label} ({self.phone_number})"
		return label

	def __str__(self):
		return self.display_label()


class Message(models.Model):
	class MessageType(models.TextChoices):
		TEXT = "text", "Text"
		AUDIO = "audio", "Audio"
		IMAGE = "image", "Image"
		VIDEO = "video", "Video"
		OTHER = "other", "Other"

	class Direction(models.TextChoices):
		INBOUND = "inbound", "Inbound"
		OUTBOUND = "outbound", "Outbound"

	external_id = models.CharField(max_length=128, unique=True)
	user = models.ForeignKey(ChatUser, on_delete=models.CASCADE, related_name="messages")
	content = models.TextField(blank=True)
	from_me = models.BooleanField(default=False, db_index=True)
	direction = models.CharField(max_length=16, choices=Direction.choices, default=Direction.INBOUND, db_index=True)
	chat_jid = models.CharField(max_length=128, blank=True, default="", db_index=True)
	sender_wa_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
	recipient_wa_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
	quoted_external_id = models.CharField(max_length=128, blank=True, default="", db_index=True)
	media_url = models.URLField(blank=True, default="")
	media_file = models.FileField(upload_to="ingesta/audio/", blank=True, null=True)
	media_mime_type = models.CharField(max_length=100, blank=True, default="")
	message_type = models.CharField(
		max_length=16,
		choices=MessageType.choices,
		default=MessageType.OTHER,
	)
	raw_data = models.JSONField(default=dict)
	timestamp = models.DateTimeField()
	processed = models.BooleanField(default=False)

	class Meta:
		ordering = ["-timestamp"]
		indexes = [
			models.Index(fields=["external_id"]),
			models.Index(fields=["timestamp"]),
			models.Index(fields=["message_type"]),
		]

	def __str__(self):
		return f"{self.external_id} - {self.message_type}"

	@property
	def is_media_message(self) -> bool:
		return self.message_type in {
			self.MessageType.AUDIO,
			self.MessageType.IMAGE,
			self.MessageType.VIDEO,
		}

	@property
	def has_media_file(self) -> bool:
		return bool(self.media_file)

	@property
	def has_encrypted_media_file(self) -> bool:
		if not self.has_media_file:
			return False
		name = str(getattr(self.media_file, "name", "") or str(self.media_file)).lower()
		return name.endswith(".enc")

	@property
	def has_usable_media_file(self) -> bool:
		return self.has_media_file and not self.has_encrypted_media_file

	@property
	def media_state(self) -> str:
		if not self.is_media_message:
			return "NON_MEDIA"
		if self.has_usable_media_file:
			return "AVAILABLE"
		if self.has_encrypted_media_file:
			return "ENCRYPTED_FILE"
		return "NO_MEDIA"


class UserInteraction(models.Model):
	class InteractionType(models.TextChoices):
		CALL = "call", "Call"
		NOTE = "note", "Note"
		OTHER = "other", "Other"

	class Direction(models.TextChoices):
		INBOUND = "inbound", "Inbound"
		OUTBOUND = "outbound", "Outbound"

	user = models.ForeignKey(ChatUser, on_delete=models.CASCADE, related_name="interactions")
	interaction_type = models.CharField(max_length=16, choices=InteractionType.choices, default=InteractionType.CALL)
	from_me = models.BooleanField(default=True, db_index=True)
	direction = models.CharField(max_length=16, choices=Direction.choices, default=Direction.OUTBOUND, db_index=True)
	occurred_at = models.DateTimeField(db_index=True)
	duration_seconds = models.PositiveIntegerField(null=True, blank=True)
	is_video = models.BooleanField(default=False)
	source = models.CharField(max_length=40, default="csv", db_index=True)
	source_ref = models.CharField(max_length=128, blank=True, default="", db_index=True)
	content = models.TextField(blank=True, default="")
	raw_data = models.JSONField(default=dict)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-occurred_at", "-id"]
		indexes = [
			models.Index(fields=["user", "occurred_at"]),
			models.Index(fields=["source", "occurred_at"]),
		]

	def __str__(self):
		return f"{self.user_id} {self.interaction_type} {self.occurred_at.isoformat()}"


class IngestionControl(models.Model):
	instance = models.OneToOneField(EvolutionInstance, on_delete=models.CASCADE, related_name="ingestion_control")
	last_sync_timestamp = models.DateTimeField()

	def __str__(self):
		return f"{self.instance.instance_name} @ {self.last_sync_timestamp.isoformat()}"


class SummaryExecutionControl(models.Model):
	class Status(models.TextChoices):
		RUNNING = "running", "Running"
		COMPLETED = "completed", "Completed"
		FAILED = "failed", "Failed"
		SKIPPED = "skipped", "Skipped"

	run_key = models.CharField(max_length=40, unique=True)
	slot_start = models.DateTimeField(db_index=True)
	slot_end = models.DateTimeField(db_index=True)
	status = models.CharField(max_length=16, choices=Status.choices, default=Status.RUNNING, db_index=True)
	started_at = models.DateTimeField(auto_now_add=True)
	finished_at = models.DateTimeField(null=True, blank=True)
	detail = models.TextField(blank=True, default="")

	eligible_users = models.PositiveIntegerField(default=0)
	processed_users = models.PositiveIntegerField(default=0)
	skipped_users = models.PositiveIntegerField(default=0)
	failed_users = models.PositiveIntegerField(default=0)
	processed_text_messages = models.PositiveIntegerField(default=0)
	daily_summaries_created = models.PositiveIntegerField(default=0)
	daily_summaries_updated = models.PositiveIntegerField(default=0)
	monthly_summaries_created = models.PositiveIntegerField(default=0)
	monthly_summaries_updated = models.PositiveIntegerField(default=0)
	prompt_tokens = models.PositiveIntegerField(default=0)
	completion_tokens = models.PositiveIntegerField(default=0)
	total_tokens = models.PositiveIntegerField(default=0)
	meta = models.JSONField(default=dict)

	class Meta:
		ordering = ["-slot_start", "-started_at"]

	def __str__(self):
		return f"{self.run_key} [{self.status}]"


class DailyTextSummary(models.Model):
	user = models.ForeignKey(ChatUser, on_delete=models.CASCADE, related_name="daily_text_summaries")
	summary_date = models.DateField(db_index=True)
	text = models.TextField(blank=True, default="")
	has_data = models.BooleanField(default=False)
	pending_items = models.JSONField(default=list)
	mentioned_people = models.JSONField(default=list)
	deadlines = models.JSONField(default=list)
	payment_promises = models.JSONField(default=list)
	source_message_count = models.PositiveIntegerField(default=0)
	source_last_message_ts = models.DateTimeField(null=True, blank=True)
	prompt_tokens = models.PositiveIntegerField(default=0)
	completion_tokens = models.PositiveIntegerField(default=0)
	total_tokens = models.PositiveIntegerField(default=0)
	last_execution = models.ForeignKey(
		SummaryExecutionControl,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="daily_summaries",
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-summary_date", "-updated_at"]
		unique_together = [("user", "summary_date")]
		indexes = [
			models.Index(fields=["summary_date"]),
			models.Index(fields=["user", "summary_date"]),
		]

	def __str__(self):
		return f"{self.user_id} {self.summary_date.isoformat()}"


class MonthlyTextSummary(models.Model):
	user = models.ForeignKey(ChatUser, on_delete=models.CASCADE, related_name="monthly_text_summaries")
	year = models.PositiveSmallIntegerField(db_index=True)
	month = models.PositiveSmallIntegerField(db_index=True)
	text = models.TextField(blank=True, default="")
	has_data = models.BooleanField(default=False)
	pending_items = models.JSONField(default=list)
	mentioned_people = models.JSONField(default=list)
	deadlines = models.JSONField(default=list)
	payment_promises = models.JSONField(default=list)
	source_message_count = models.PositiveIntegerField(default=0)
	source_last_message_ts = models.DateTimeField(null=True, blank=True)
	prompt_tokens = models.PositiveIntegerField(default=0)
	completion_tokens = models.PositiveIntegerField(default=0)
	total_tokens = models.PositiveIntegerField(default=0)
	revision = models.PositiveIntegerField(default=1)
	is_current = models.BooleanField(default=True, db_index=True)
	last_execution = models.ForeignKey(
		SummaryExecutionControl,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="monthly_summaries",
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-year", "-month", "-revision"]
		indexes = [
			models.Index(fields=["user", "year", "month"]),
			models.Index(fields=["year", "month", "is_current"]),
		]

	def __str__(self):
		return f"{self.user_id} {self.year}-{self.month:02d} r{self.revision}"
