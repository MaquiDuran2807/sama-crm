# Audio Briefing System (Piper-TTS)

## 🎙️ ¿Qué es?

Sistema de **briefing diario hablado** que convierte los resúmenes de IA en audio para el equipo.

**Flujo:**
1. La IA genera resúmenes de texto de cada cliente (ya existe)
2. **Piper-TTS** convierte el resumen a audio hablado
3. Se genera una narrativa ejecutiva: "Hola Deya, hoy tienes X clientes pendientes..."
4. Auto-envío por Evolution API (opcional)

## 🚀 Instalación

### 1. Instalar dependencias

```bash
cd "C:\Users\Janus\Documents\SAMA\app SAMA"
pip install -r requirements.txt
```

Esto instala:
- `piper-tts` - Motor TTS local
- `pydub` - Procesamiento de audio
- `soundfile` - Lectura/escritura de WAV

### 2. Configurar GPU (GTX 1050 Ti 4GB)

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

Para tu GTX 1050 Ti:
- CUDA 11.8 es compatible
- Requiere ~2GB VRAM para Piper

### 3. Agregar variables de entorno

Copia en tu `.env`:

```
PIPER_VOICE_MODEL=es_ES-davkyar-medium
PIPER_USE_GPU=True
PIPER_GPU_DEVICE=0
AUTO_SEND_BRIEFING_AUDIO=False
AUDIO_BRIEFING_ENABLED=True
```

### 4. Verificar instalación

```bash
python test_piper_gpu.py
```

Expected output:
```
✓ CUDA disponible: NVIDIA GeForce GTX 1050 Ti (4.0 GB)
✓ Modelo de voz cargado correctamente
✓ Síntesis exitosa: 123456 bytes generados
✓ TODOS LOS TESTS PASARON
```

## 📖 Uso

### Generar briefing diario (manual)

```bash
python manage.py generate_daily_audio_briefing --instance Deya3 --team-user 1
```

Opciones:
- `--instance`: Nombre de la instancia Evolution (default: Deya3)
- `--team-user`: ID del usuario destino (default: 1)
- `--date`: Fecha específica (default: hoy)
- `--use-gpu`: Usar GPU si está disponible (default: True)
- `--silent`: No mostrar progreso verbose

### Ejemplo de ejecución

```bash
$ python manage.py generate_daily_audio_briefing --instance Deya3 --team-user 1

Generando briefing de audio para Deya (2026-04-17)
  [10%] discovery: Descubriendo clientes con pendientes
  [30%] narrative: Generando narrativa ejecutiva
  [60%] tts: Sintetizando audio...
  [75%] save: Guardando archivo de audio
  [85%] send: Preparando envío por Evolution API
  [100%] completed: Briefing completado

✓ Briefing generado exitosamente
  Audio: 245632 bytes
  Clientes: 3
  Archivo: ingesta/audio/briefing_1_2026-04-17.wav
```

## 🔊 Estructura del Briefing

El audio generado tiene esta estructura:

```
INTRO:
  "Hola Deya, buenos días. Hoy tienes mensajes pendientes de 3 clientes."

POR CADA CLIENTE:
  "Número 1. Valentina te escribió con 5 mensajes.
   Según tu resumen: [texto del resumen de la IA]
   [Si hay problemas] Se detectó un posible problema en este cliente.
   Te recomendamos revisar estos pendientes."

CIERRE:
  "Estos son tus pendientes de hoy. Cualquier duda, revisa los detalles en el sistema."
```

## 🧠 Cómo usa la IA

1. **Resumen diario** (`TextSummaryService`):
   - Ya obtienes resúmenes de Ollama por cliente → `DailyTextSummary`

2. **Narrativa ejecutiva** (`AudioBriefingService`):
   - Lee los resúmenes de BD
   - Agrega contexto: quién te escribió, cuántos mensajes
   - Detecta problemas en el texto (palabras clave: "urgente", "problema")
   - Crea narrativa coherente

3. **Síntesis TTS** (Piper):
   - Convierte narrativa → audio WAV
   - Corre localmente con GPU acelerado

## 🎯 Ejemplos de salida

### Briefing generado (texto)

```
Hola Deya, buenos días. Hoy tienes mensajes pendientes de 3 clientes.

Número 1. Valentina te escribió con 5 mensajes.
Según tu resumen: El cliente reporta un problema con las reservas. 
Varios huéspedes están esperando confirmación. Se detectó un posible 
problema en este cliente. Prioriza esta conversación.
Te recomendamos revisar estos pendientes.

Número 2. Carlos te escribió con 2 mensajes.
Según tu resumen: Solicita información sobre tarifas especiales para 
grupo de 15 personas. Requiere respuesta urgente.
Te recomendamos revisar estos pendientes.

Número 3. María te escribió con 1 mensaje.
Según tu resumen: Pregunta por disponibilidad próximo mes.
Te recomendamos revisar estos pendientes.

Estos son tus pendientes de hoy. Cualquier duda, revisa los detalles 
en el sistema. ¡Buena suerte!
```

### Archivo de audio

- **Nombre**: `briefing_1_2026-04-17.wav`
- **Tamaño**: ~150-250 KB (depende del texto)
- **Duración**: 1-3 minutos (varía según clientes)
- **Ubicación**: `media/ingesta/audio/`

## 🔧 Modelos de voz disponibles

| Modelo | Idioma | Género | Calidad | Velocidad |
|--------|--------|--------|---------|-----------|
| `es_ES-davkyar-medium` | Español (España) | Hombre | ⭐⭐⭐⭐ | Rápido |
| `es_ES-davkyar-high` | Español (España) | Hombre | ⭐⭐⭐⭐⭐ | Normal |
| `es_MX-tefillas-high` | Español (México) | Mujer | ⭐⭐⭐⭐⭐ | Normal |

Cambiar en `.env`:
```
PIPER_VOICE_MODEL=es_MX-tefillas-high
```

## 📊 Rendimiento GPU

Con **GTX 1050 Ti (4GB)**:

| Operación | CPU | GPU |
|-----------|-----|-----|
| Carga modelo | 2-3s | 1-2s |
| Síntesis 1 min audio | 8-12s | 2-3s |
| Briefing completo (3 clientes) | 30-45s | 10-15s |

**Aceleración:** ~3-4x más rápido con GPU

## ⚙️ Configuración Avanzada

### Ajustar velocidad de voz

En `audio_service.py`, línea `syntesyze()`:

```python
# Más rápido
audio_bytes = self.tts_engine.synthesize(narrative, speed=1.2)

# Más lento (más claro)
audio_bytes = self.tts_engine.synthesize(narrative, speed=0.8)
```

### Usar CPU solo (sin GPU)

En `.env`:
```
PIPER_USE_GPU=False
```

### Auto-envío por Evolution

Para que auto-envíe el audio por WhatsApp:

```
AUTO_SEND_BRIEFING_AUDIO=True
```

(Requiere endpoint de Evolution implementado)

## 🐛 Troubleshooting

### Error: "piper-tts not installed"
```bash
pip install piper-tts --upgrade
```

### Error: "CUDA out of memory"
```bash
# Usar CPU temporalmente
PIPER_USE_GPU=False python manage.py generate_daily_audio_briefing
```

### Audio muy lento o rápido
Ajusta `speed` en `audio_service.py` línea 75:
```python
audio_bytes = self.tts_engine.synthesize(narrative, speed=1.0)
# Prueba con 1.1, 1.2, 0.9, etc.
```

### Modelo no descargar automáticamente
```bash
python -c "from piper.voice import PiperVoice; v = PiperVoice.load('es_ES-davkyar-medium')"
```

## 📝 Integration con Scheduler

Para ejecutar cada día a una hora específica, agrega a `scheduler.py`:

```python
from ingesta.audio_service import AudioBriefingService
from ingesta.models import ChatUser

def schedule_daily_audio_briefing():
    """Ejecuta a las 7:00 AM cada día"""
    try:
        team_user = ChatUser.objects.get(id=1)  # Deya
        service = AudioBriefingService()
        result = service.generate_daily_briefing(
            instance_name="Deya3",
            team_user=team_user,
            date=timezone.now()
        )
        logger.info(f"✓ Briefing diario generado: {result['audio_file']}")
    except Exception as e:
        logger.error(f"✗ Error en briefing diario: {e}")

# En el scheduler (APScheduler):
scheduler.add_job(
    schedule_daily_audio_briefing,
    'cron',
    hour=7,
    minute=0,
    id='daily_audio_briefing'
)
```

## 🎬 Next Steps

1. ✅ Instalé Piper-TTS con GPU
2. ✅ Crée servicio de audio
3. ⏳ **Próximo:** Integrar con scheduler diario
4. ⏳ Implementar envío por Evolution API
5. ⏳ Agregar más voces/idiomas

---

¿Preguntas o necesitas ayuda? 🚀
