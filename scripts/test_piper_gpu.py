"""
Script de prueba para verificar Piper-TTS con GPU.

Uso:
    python test_piper_gpu.py
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_piper_installation():
    """Verifica que piper-tts esté instalado."""
    try:
        import piper
        logger.info("✓ piper-tts instalado")
        return True
    except ImportError:
        logger.error("✗ piper-tts NO instalado. Ejecuta: pip install piper-tts")
        return False


def test_gpu_availability():
    """Verifica si CUDA/GPU está disponible."""
    try:
        import torch

        cuda_available = torch.cuda.is_available()
        if cuda_available:
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0)
            total_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            logger.info(f"✓ CUDA disponible: {device_name} ({total_memory:.1f} GB)")
            return True
        else:
            logger.warning("⚠ CUDA no disponible (usando CPU)")
            return False
    except ImportError:
        logger.warning("⚠ PyTorch no instalado (se usará CPU)")
        return False


def test_voice_model_load():
    """Carga el modelo de voz español."""
    try:
        from piper.voice import PiperVoice

        logger.info("Cargando modelo de voz es_ES-davkyar-medium...")
        voice = PiperVoice.load("es_ES-davkyar-medium")
        logger.info("✓ Modelo de voz cargado correctamente")
        return voice
    except Exception as e:
        logger.error(f"✗ Error cargando modelo: {e}")
        return None


def test_synthesis(voice):
    """Prueba síntesis de texto a voz."""
    if not voice:
        logger.error("✗ No hay modelo de voz cargado")
        return False

    try:
        import io

        text = "Hola Deya, buenos días. Hoy tienes mensajes pendientes de tus clientes."
        logger.info(f"Sintetizando: {text}")

        audio_buffer = io.BytesIO()
        voice.synthesize(text, audio_file=audio_buffer)
        audio_bytes = audio_buffer.getvalue()

        logger.info(f"✓ Síntesis exitosa: {len(audio_bytes)} bytes generados")
        return True
    except Exception as e:
        logger.error(f"✗ Error en síntesis: {e}")
        return False


def main():
    logger.info("=" * 60)
    logger.info("TEST DE PIPER-TTS + GPU")
    logger.info("=" * 60)

    # Test 1: Instalación
    logger.info("\n[1/4] Verificando instalación...")
    if not test_piper_installation():
        sys.exit(1)

    # Test 2: GPU
    logger.info("\n[2/4] Verificando GPU...")
    gpu_available = test_gpu_availability()

    # Test 3: Cargar modelo
    logger.info("\n[3/4] Cargando modelo de voz...")
    voice = test_voice_model_load()
    if not voice:
        sys.exit(1)

    # Test 4: Síntesis
    logger.info("\n[4/4] Probando síntesis...")
    if not test_synthesis(voice):
        sys.exit(1)

    logger.info("\n" + "=" * 60)
    logger.info("✓ TODOS LOS TESTS PASARON")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
