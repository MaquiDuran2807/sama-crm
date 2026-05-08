from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ingesta.models import ChatUser, Message
from ingesta.summary_service import TextSummaryService


class Command(BaseCommand):
	help = "Comando de prueba: procesa resúmenes IA para un único usuario de las últimas horas."

	def add_arguments(self, parser):
		parser.add_argument(
			"--user-id",
			type=int,
			help="ID del usuario a procesar. Si se omite, toma el primero con mensajes de texto.",
		)
		parser.add_argument(
			"--lookback-hours",
			type=int,
			default=12,
			help="Horas hacia atrás para procesar. Por defecto 12.",
		)
		parser.add_argument(
			"--show-messages",
			action="store_true",
			help="Muestra los mensajes procesados antes del resumen.",
		)

	def handle(self, *args, **options):
		user_id = options.get("user_id")
		lookback_hours = int(options.get("lookback_hours", 12))
		show_messages = bool(options.get("show_messages", False))

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
				.first()
			)
			if not user:
				self.stdout.write(self.style.ERROR("No hay usuarios con mensajes de texto en la ventana"))
				return

		messages = list(
			Message.objects.filter(
				user=user,
				message_type=Message.MessageType.TEXT,
				timestamp__gte=start_time,
			).order_by("timestamp")
		)

		if not messages:
			self.stdout.write(self.style.WARNING(f"Usuario {user.display_label()} sin mensajes en ventana."))
			return

		self.stdout.write(self.style.SUCCESS(f"Usuario seleccionado: {user.display_label()} (ID={user.id})"))
		self.stdout.write(f"Mensajes encontrados: {len(messages)} desde {start_time.isoformat()}")

		if show_messages:
			self.stdout.write("\n=== MENSAJES ===")
			for msg in messages:
				role = "ASESOR" if msg.from_me else "CLIENTE"
				content = (msg.content or "")[:60] + ("..." if len(msg.content or "") > 60 else "")
				self.stdout.write(f"  {msg.timestamp.strftime('%H:%M')} | {role:8} | {content}")

		self.stdout.write("\n=== GENERANDO RESUMEN ===\n")

		service = TextSummaryService()
		slot_start = start_time
		slot_end = now
		run_key = f"test_user_{user.id}_{now.timestamp()}"

		try:
			log = service.run_for_slot(
				slot_start=slot_start,
				slot_end=slot_end,
				run_key=run_key,
				force=False,
			)

			self.stdout.write(f"Status: {log.status}")
			self.stdout.write(f"Procesados: {log.processed_users} usuarios")
			self.stdout.write(f"Mensajes textuales procesados: {log.processed_text_messages}")
			self.stdout.write(f"Resúmenes diarios: {log.daily_summaries_created} creados, {log.daily_summaries_updated} actualizados")
			self.stdout.write(f"Resúmenes mensuales: {log.monthly_summaries_created} creados, {log.monthly_summaries_updated} actualizados")
			self.stdout.write(f"Tokens: {log.prompt_tokens} entrada + {log.completion_tokens} salida = {log.total_tokens} total")

			if log.status != "completed":
				self.stdout.write(self.style.WARNING(f"Detalle: {log.detail}"))

			if log.detail:
				self.stdout.write(f"\nDetalle: {log.detail}")

			self.stdout.write(self.style.SUCCESS("\n✓ Procesamiento completado."))

		except Exception as exc:
			self.stdout.write(self.style.ERROR(f"\n✗ Error: {exc}"))
			import traceback

			self.stdout.write(traceback.format_exc())
