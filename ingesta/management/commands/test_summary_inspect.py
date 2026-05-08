from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ingesta.models import ChatUser, DailyTextSummary, Message


class Command(BaseCommand):
	help = "Prueba simple: verifica datos y estructura sin llamar a IA."

	def add_arguments(self, parser):
		parser.add_argument(
			"--user-id",
			type=int,
			help="ID del usuario. Si se omite, toma el primero con mensajes.",
		)
		parser.add_argument(
			"--lookback-hours",
			type=int,
			default=12,
			help="Horas hacia atrás. Por defecto 12.",
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
				self.stdout.write(self.style.ERROR("No hay usuarios con mensajes de texto."))
				return

		messages = list(
			Message.objects.filter(
				user=user,
				message_type=Message.MessageType.TEXT,
				timestamp__gte=start_time,
			).order_by("timestamp")
		)

		self.stdout.write(f"USUARIO: {user.display_label()} (ID={user.id})")
		self.stdout.write(f"VENTANA: {start_time.isoformat()} -> {now.isoformat()}")
		self.stdout.write(f"MENSAJES TEXTO: {len(messages)}")
		self.stdout.write("")

		for msg in messages:
			role = "📤 ASESOR" if msg.from_me else "📥 CLIENTE"
			content = (msg.content or "")[:80]
			self.stdout.write(f"  {msg.timestamp.strftime('%m-%d %H:%M')} | {role} | {content}")

		by_day = {}
		for msg in messages:
			day = msg.timestamp.date()
			if day not in by_day:
				by_day[day] = []
			by_day[day].append(msg)

		self.stdout.write("")
		self.stdout.write(f"RESÚMENES DIARIOS EXISTENTES:")
		for day in sorted(by_day.keys()):
			existing = DailyTextSummary.objects.filter(user=user, summary_date=day).first()
			if existing:
				state = "✓" if existing.has_data else "✗"
				self.stdout.write(
					f"  {state} {day} | {existing.total_tokens} tokens | msgs={existing.source_message_count} | '{existing.text[:50]}...'"
				)
			else:
				self.stdout.write(f"  ⏳ {day} | SIN RESUMEN")

		self.stdout.write("")
		self.stdout.write(self.style.SUCCESS("✓ Estructura validada correctamente."))
