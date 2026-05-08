from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ingesta.models import (ChatUser, DailyTextSummary, Message,
                            SummaryExecutionControl)


class Command(BaseCommand):
	help = "Simula procesamiento de resúmenes sin llamada a IA (para demo/test)."

	def add_arguments(self, parser):
		parser.add_argument(
			"--user-id",
			type=int,
			help="ID del usuario. Si se omite, toma el primero.",
		)
		parser.add_argument(
			"--lookback-hours",
			type=int,
			default=12,
			help="Horas hacia atrás (default 12).",
		)

	def handle(self, *args, **options):
		user_id = options.get("user_id")
		lookback_hours = int(options.get("lookback_hours", 12))

		now = timezone.now()
		start_time = now - timedelta(hours=lookback_hours)

		if user_id:
			try:
				user = ChatUser.objects.get(id=user_id)
			except ChatUser.DoesNotExist:
				self.stdout.write(self.style.ERROR(f"Usuario {user_id} no encontrado."))
				return
		else:
			user = (
				ChatUser.objects.filter(
					messages__message_type=Message.MessageType.TEXT,
					messages__timestamp__gte=start_time,
				)
				.distinct()
				.order_by("-last_interaction")
				.first()
			)
			if not user:
				self.stdout.write(self.style.ERROR("No hay usuarios con mensajes."))
				return

		messages = list(
			Message.objects.filter(
				user=user,
				message_type=Message.MessageType.TEXT,
				timestamp__gte=start_time,
			).order_by("timestamp")
		)

		if not messages:
			self.stdout.write(self.style.WARNING(f"Usuario sin mensajes en ventana."))
			return

		self.stdout.write(self.style.SUCCESS(f"📋 USUARIO: {user.display_label()} (ID={user.id})"))
		self.stdout.write(f"   Ventana: {start_time.strftime('%Y-%m-%d %H:%M')} -> {now.strftime('%Y-%m-%d %H:%M')}")
		self.stdout.write(f"   Mensajes: {len(messages)}\n")

		by_day = {}
		for msg in messages:
			day = msg.timestamp.date()
			if day not in by_day:
				by_day[day] = []
			by_day[day].append(msg)

		exec_log = SummaryExecutionControl.objects.create(
			run_key=f"demo_{user.id}_{now.timestamp()}",
			slot_start=start_time,
			slot_end=now,
			status=SummaryExecutionControl.Status.RUNNING,
			eligible_users=1,
		)

		created_count = 0
		updated_count = 0

		for day, day_messages in by_day.items():
			day_messages = sorted(day_messages, key=lambda m: m.timestamp)
			source_count = len(day_messages)
			source_last_ts = day_messages[-1].timestamp

			unresolved = 0
			last_from_me = True
			for msg in day_messages:
				if msg.from_me:
					last_from_me = True
				else:
					if last_from_me:
						unresolved += 1
					last_from_me = False
			if not last_from_me:
				unresolved += 1

			excerpt = " | ".join(
				[(msg.content or "")[:20] for msg in day_messages[:3]]
			)

			existing = DailyTextSummary.objects.filter(user=user, summary_date=day).first()
			if existing and existing.source_message_count == source_count and existing.source_last_message_ts == source_last_ts:
				self.stdout.write(f"  ↷ {day} (sin cambios, omitido)")
				continue

			summary_text = f"Resumen del {day}: {source_count} msgs, {unresolved} no respondidos. Contenido: {excerpt}"
			prompt_tokens = 150 + len(summary_text)
			completion_tokens = 100

			if not existing:
				existing = DailyTextSummary.objects.create(
					user=user,
					summary_date=day,
					text=summary_text,
					has_data=True,
					pending_items=[],
					mentioned_people=[],
					deadlines=[],
					payment_promises=[],
					source_message_count=source_count,
					source_last_message_ts=source_last_ts,
					prompt_tokens=prompt_tokens,
					completion_tokens=completion_tokens,
					total_tokens=prompt_tokens + completion_tokens,
					last_execution=exec_log,
				)
				created_count += 1
				self.stdout.write(self.style.SUCCESS(f"  ✓ {day} CREADO ({existing.total_tokens} tokens)"))
			else:
				existing.text = summary_text
				existing.source_message_count = source_count
				existing.source_last_message_ts = source_last_ts
				existing.prompt_tokens = prompt_tokens
				existing.completion_tokens = completion_tokens
				existing.total_tokens = prompt_tokens + completion_tokens
				existing.last_execution = exec_log
				existing.save(
					update_fields=[
						"text",
						"source_message_count",
						"source_last_message_ts",
						"prompt_tokens",
						"completion_tokens",
						"total_tokens",
						"last_execution",
						"updated_at",
					]
				)
				updated_count += 1
				self.stdout.write(self.style.WARNING(f"  ※ {day} ACTUALIZADO ({existing.total_tokens} tokens)"))

		exec_log.processed_users = 1
		exec_log.processed_text_messages = len(messages)
		exec_log.daily_summaries_created = created_count
		exec_log.daily_summaries_updated = updated_count
		exec_log.prompt_tokens = sum(
			DailyTextSummary.objects.filter(
				user=user, last_execution=exec_log
			).values_list("prompt_tokens", flat=True)
		)
		exec_log.completion_tokens = sum(
			DailyTextSummary.objects.filter(
				user=user, last_execution=exec_log
			).values_list("completion_tokens", flat=True)
		)
		exec_log.total_tokens = exec_log.prompt_tokens + exec_log.completion_tokens
		exec_log.status = SummaryExecutionControl.Status.COMPLETED
		exec_log.detail = f"Procesado {len(by_day)} días"
		exec_log.finished_at = timezone.now()
		exec_log.save()

		self.stdout.write("")
		self.stdout.write(self.style.SUCCESS("📊 RESULTADO DE EJECUCIÓN"))
		self.stdout.write(f"   Días procesados: {len(by_day)}")
		self.stdout.write(f"   Resúmenes creados: {created_count}")
		self.stdout.write(f"   Resúmenes actualizados: {updated_count}")
		self.stdout.write(f"   Tokens totales: {exec_log.total_tokens} (entrada: {exec_log.prompt_tokens}, salida: {exec_log.completion_tokens})")
		self.stdout.write(f"   Status: {exec_log.status}")
		self.stdout.write("")
		self.stdout.write(f"   Run Key: {exec_log.run_key}")
		self.stdout.write(f"   Exec ID: {exec_log.id}")
		self.stdout.write("")
		self.stdout.write(self.style.SUCCESS("✓ Demo completado. Los resúmenes están marcados como PROCESADOS."))
