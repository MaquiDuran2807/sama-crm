# Audio Briefing System

## Overview

Converts daily AI summaries into spoken audio using Piper-TTS, then auto-sends via Evolution API.

**Flow:**
1. AI generates text summaries (existing feature)
2. `AudioBriefingService` compiles executive narrative
3. Piper-TTS generates `.wav` audio
4. Evolution API sends audio to configured contacts (optional)

## Components

| File | Purpose |
|------|---------|
| `ingesta/audio_service.py` | TTS engine + briefing generator |
| `ingesta/management/commands/generate_daily_audio_briefing.py` | Django management command |
| `ingesta/views.py` (`AudioBriefingTriggerView`) | HTTP trigger endpoint |

## Configuration

Settings in `.env`:

```env
PIPER_VOICE_MODEL=es_ES-davefx-medium
PIPER_VOICE_FALLBACKS=es_ES-davefx-medium,es_MX-claude-high,es_MX-ald-medium
PIPER_USE_GPU=True
PIPER_GPU_DEVICE=0
AUTO_SEND_BRIEFING_AUDIO=False
AUDIO_BRIEFING_ENABLED=True
AUDIO_BRIEFING_MAX_CLIENTS=20
AUDIO_BRIEFING_MAX_SUMMARY_CHARS=380
AUDIO_BRIEFING_MAX_SAMPLE_CHARS=160
AUDIO_BRIEFING_MAX_TOTAL_CHARS=12000
AUDIO_BRIEFING_TTS_SPEED=0.7
```

## Usage

```bash
# Generate briefing for all eligible clients
python manage.py generate_daily_audio_briefing

# Via API
POST /ingesta/api/trigger-audio-briefing/
```

## Audio Quality

- Sample rate: 22050 Hz (Piper default)
- Output: WAV format
- Speed: 0.7x for clarity
- Multi-voice fallback chain configured via env
