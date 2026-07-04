"""
Demostración: Cómo funciona el sistema de briefing de audio completo

Ejecutar:
    python manage.py shell < demo_audio_briefing.py

O interactivo:
    python manage.py shell
    >>> exec(open('demo_audio_briefing.py').read())
"""

import json
from datetime import datetime, timedelta
from django.utils import timezone
from ingesta.models import ChatUser, Message, DailyTextSummary
from ingesta.audio_service import AudioBriefingService, PiperTTSEngine


def demo_complete_flow():
    """Demostración completa del flujo de audio briefing."""

    print("\n" + "=" * 70)
    print("DEMO: Sistema de Audio Briefing Completo")
    print("=" * 70)

    # ============================================================
    # PASO 1: Verificar usuarios y resúmenes existentes
    # ============================================================
    print("\n[PASO 1] Verificando datos de prueba...")

    team_user = ChatUser.objects.first()
    if not team_user:
        print("  ✗ No hay usuarios en la BD. Debes ejecutar:")
        print("    python manage.py seed_instances.py")
        return

    print(f"  ✓ Equipo: {team_user.display_label()} (ID: {team_user.id})")

    # Verificar que hay resúmenes de hoy
    today = timezone.now().date()
    summaries = DailyTextSummary.objects.filter(summary_date=today)

    if not summaries.exists():
        print(f"  ⚠ No hay resúmenes para hoy ({today})")
        print("  Nota: Ejecuta primero: python manage.py run_text_summaries")
        today = summaries.first().summary_date if summaries.exists() else today
        summaries = DailyTextSummary.objects.filter(summary_date=today)

    print(f"  ✓ Encontrados {summaries.count()} resúmenes para la fecha")

    # ============================================================
    # PASO 2: Inicializar motor Piper-TTS
    # ============================================================
    print("\n[PASO 2] Inicializando motor Piper-TTS...")

    try:
        tts_engine = PiperTTSEngine(use_gpu=True)
        print("  ✓ Motor Piper inicializado")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return

    # ============================================================
    # PASO 3: Test de síntesis simple
    # ============================================================
    print("\n[PASO 3] Test de síntesis simple...")

    sample_text = "Hola Deya, buenos días. Hoy tienes mensajes pendientes de tus clientes."
    try:
        audio_bytes = tts_engine.synthesize(sample_text, speed=1.0)
        print(f"  ✓ Síntesis exitosa: {len(audio_bytes)} bytes")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return

    # ============================================================
    # PASO 4: Descubrir clientes con pendientes
    # ============================================================
    print("\n[PASO 4] Descubriendo clientes con pendientes...")

    briefing_service = AudioBriefingService()
    clients = briefing_service._discover_pending_clients(timezone.now())

    if not clients:
        print("  ⚠ No hay clientes con pendientes hoy")
    else:
        print(f"  ✓ Encontrados {len(clients)} clientes con pendientes:")
        for client in clients:
            print(f"    - {client['user_name']}: {client['pending_count']} mensajes")

    # ============================================================
    # PASO 5: Generar narrativa
    # ============================================================
    print("\n[PASO 5] Generando narrativa ejecutiva...")

    narrative = briefing_service._build_narrative(team_user, timezone.now(), clients[:2])
    print("  Narrativa generada (primeros 500 chars):")
    print("  " + "-" * 66)
    for line in narrative[:500].split("\n"):
        print(f"  {line}")
    print("  " + "-" * 66)

    # ============================================================
    # PASO 6: Generar briefing completo
    # ============================================================
    print("\n[PASO 6] Generando briefing completo...")

    def progress_callback(data):
        phase = data.get("phase", "")
        progress = data.get("progress", 0)
        detail = data.get("detail", "")
        print(f"  [{progress:3d}%] {phase}: {detail}")

    result = briefing_service.generate_daily_briefing(
        instance_name="Deya3",
        team_user=team_user,
        date=timezone.now(),
        progress_callback=progress_callback,
    )

    # ============================================================
    # PASO 7: Mostrar resultados
    # ============================================================
    print("\n[PASO 7] Resultados del briefing...")

    if result.get("error"):
        print(f"  ✗ Error: {result['error']}")
    else:
        print("  ✓ Briefing generado exitosamente")
        print(f"    Audio size: {result['audio_size_bytes']} bytes")
        print(f"    Duración estimada: ~{result['audio_size_bytes'] / 8000:.1f}s")
        print(f"    Clientes procesados: {len(result['clients'])}")
        print(f"    Archivo: {result['audio_file']}")
        print(f"    Enviado por Evolution: {result['sent_to_evolution']}")

    # ============================================================
    # PASO 8: Mostrar narrativa completa
    # ============================================================
    if result.get("narrative"):
        print("\n[PASO 8] Narrativa completa...")
        print("  " + "-" * 66)
        for line in result["narrative"].split("\n"):
            print(f"  {line}")
        print("  " + "-" * 66)

    print("\n✓ Demo completada!")
    print("=" * 70)


def demo_single_briefing():
    """Demo simplificada: Solo genera el audio para hoy."""

    print("\nDemo Rápida: Generar Audio Briefing de Hoy")
    print("=" * 70)

    from ingesta.audio_service import AudioBriefingService

    service = AudioBriefingService()
    team_user = ChatUser.objects.first()

    if not team_user:
        print("✗ No hay usuarios. Ejecuta: python manage.py seed_instances.py")
        return

    result = service.generate_daily_briefing(
        instance_name="Deya3",
        team_user=team_user,
        date=timezone.now(),
    )

    print(f"Audio generado: {result['audio_file']}")
    print(f"Tamaño: {result['audio_size_bytes']} bytes")
    print(f"Clientes: {len(result['clients'])}")


# Ejecutar
if __name__ == "__main__":
    demo_complete_flow()
    # demo_single_briefing()
