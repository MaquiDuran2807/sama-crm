"""
Management command para generar briefing de audio diario.

Uso:
    python manage.py generate_daily_audio_briefing --instance Deya3 --team-user 1 --date 2026-04-17
"""

from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingesta.models import ChatUser
from ingesta.audio_service import AudioBriefingService


class Command(BaseCommand):
    help = "Genera briefing ejecutivo diario en audio"

    def add_arguments(self, parser):
        parser.add_argument(
            "--instance",
            type=str,
            default="Deya3",
            help="Nombre de la instancia Evolution",
        )
        parser.add_argument(
            "--team-user",
            type=int,
            default=None,
            help="ID del usuario del equipo (opcional; si se omite usa fallback automático)",
        )
        parser.add_argument(
            "--date",
            type=str,
            help="Fecha del briefing (ISO format: 2026-04-17). Default: hoy",
        )
        parser.add_argument(
            "--use-gpu",
            action="store_true",
            default=True,
            help="Usar GPU si está disponible (default: True)",
        )
        parser.add_argument(
            "--silent",
            action="store_true",
            help="No mostrar progreso verbose",
        )

    def handle(self, *args, **options):
        instance_name = options["instance"]
        team_user_id = options["team_user"]
        date_str = options.get("date")
        silent = options.get("silent", False)

        # Resolver fecha
        if date_str:
            try:
                date = datetime.fromisoformat(date_str)
                if date.tzinfo is None:
                    date = timezone.make_aware(date)
            except ValueError:
                self.stdout.write(self.style.ERROR(f"Fecha inválida: {date_str}"))
                return
        else:
            date = timezone.now()

        # Obtener usuario del equipo (fallback automático)
        team_user = None
        if team_user_id:
            team_user = ChatUser.objects.filter(id=team_user_id).first()
            if not team_user:
                self.stdout.write(self.style.WARNING(f"Usuario {team_user_id} no encontrado; usando fallback automático"))
        if not team_user:
            team_user = ChatUser.objects.filter(is_customer=False).order_by("-last_interaction", "id").first()
        if not team_user:
            team_user = ChatUser.objects.order_by("-last_interaction", "id").first()
        if not team_user:
            self.stdout.write(self.style.ERROR("No hay usuarios disponibles en ChatUser"))
            return

        self.stdout.write(f"Generando briefing de audio para {team_user.display_label()} ({date.date()})")

        # Servicio de audio
        service = AudioBriefingService()

        # Callback de progreso
        def progress(data):
            if not silent:
                phase = data.get("phase")
                progress_val = data.get("progress", 0)
                detail = data.get("detail", "")
                self.stdout.write(f"  [{progress_val:3d}%] {phase}: {detail}")

        # Generar briefing
        result = service.generate_daily_briefing(
            instance_name=instance_name,
            team_user=team_user,
            date=date,
            force_local_only=True,
            progress_callback=progress,
        )

        # Mostrar resultado
        if result.get("error"):
            self.stdout.write(self.style.ERROR(f"✗ Error: {result['error']}"))
            return

        self.stdout.write(self.style.SUCCESS("\n✓ Briefing generado exitosamente"))
        self.stdout.write(f"  Audio: {result['audio_size_bytes']} bytes")
        self.stdout.write(f"  Clientes: {len(result['clients'])}")
        self.stdout.write(f"  Archivo: {result['audio_file']}")

        self.stdout.write(self.style.WARNING("  ⚠ Modo local: no se envía por Evolution API"))

        # Mostrar narrativa (preview)
        if not silent:
            self.stdout.write("\n--- Narrativa generada ---")
            self.stdout.write(result["narrative"][:500] + "...\n")
