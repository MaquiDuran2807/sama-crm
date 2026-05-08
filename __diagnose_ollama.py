#!/usr/bin/env python
"""Diagnóstico de conexión a Ollama y estado de resúmenes."""

import os
import sys

import django
import requests

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sama_core.settings')
django.setup()

from datetime import datetime, timedelta

from django.conf import settings

from ingesta.models import DailyTextSummary, SummaryExecutionControl

print("=" * 70)
print("DIAGNÓSTICO OLLAMA Y RESÚMENES IA")
print("=" * 70)

# 1. Verificar configuración
print("\n[1] CONFIGURACIÓN")
print("-" * 70)
ollama_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
timeout = getattr(settings, 'AI_SUMMARY_TIMEOUT_SECONDS', 90)
model = getattr(settings, 'AI_SUMMARY_MODEL', 'llama3.2')

print(f"Ollama URL: {ollama_url}")
print(f"Modelo: {model}")
print(f"Timeout: {timeout}s")
print(f"Scheduler activo: {getattr(settings, 'AI_SUMMARY_SCHEDULER_ENABLED', True)}")

# 2. Probar conectividad a Ollama
print("\n[2] PRUEBA DE CONECTIVIDAD")
print("-" * 70)
try:
    resp = requests.get(f'{ollama_url}/api/tags', timeout=5)
    print(f"✓ Conexión exitosa (HTTP {resp.status_code})")
    data = resp.json()
    models = data.get('models', [])
    print(f"Modelos disponibles: {len(models)}")
    found_model = False
    for m in models[:5]:
        name = m.get('name', 'unknown')
        print(f"  - {name}")
        if name.startswith(model):
            found_model = True
    if found_model:
        print(f"✓ Modelo '{model}' encontrado")
    else:
        print(f"⚠ Modelo '{model}' NO encontrado (tienes otros)")
except requests.exceptions.ConnectionError as e:
    print(f"✗ ERROR CONEXIÓN: {ollama_url}")
    print(f"  El servidor no está corriendo o no está accesible")
    print(f"  Detalle: {e}")
except requests.exceptions.Timeout:
    print(f"✗ ERROR TIMEOUT: {ollama_url}")
    print(f"  El servidor existe pero no responde en 5s")
except Exception as e:
    print(f"✗ ERROR: {type(e).__name__}: {e}")

# 3. Revisar logs de ejecución
print("\n[3] ÚLTIMAS CORRIDAS DE RESÚMENES")
print("-" * 70)
recent = SummaryExecutionControl.objects.order_by('-started_at')[:5]
if recent.exists():
    for log in recent:
        status_icon = "✓" if log.status == "completed" else "⚠" if log.status == "failed" else "○"
        print(f"{status_icon} {log.run_key}")
        print(f"   Status: {log.status}, Usuarios: {log.processed_users}/{log.eligible_users}")
        if log.failed_users > 0:
            print(f"   ⚠ {log.failed_users} usuarios fallidos")
        if log.detail:
            print(f"   Detalle: {log.detail}")
        print(f"   Tokens: {log.total_tokens} (prompt={log.prompt_tokens}, completion={log.completion_tokens})")
        if log.started_at and log.finished_at:
            duration = (log.finished_at - log.started_at).total_seconds()
            print(f"   Duración: {duration:.2f}s")
        print()
else:
    print("No hay registros de ejecución")

# 4. Revisar últimos resúmenes generados
print("\n[4] ÚLTIMOS RESÚMENES GENERADOS")
print("-" * 70)
recent_daily = DailyTextSummary.objects.order_by('-updated_at')[:5]
if recent_daily.exists():
    for s in recent_daily:
        has_data = "✓" if s.has_data else "✗"
        print(f"{has_data} {s.summary_date} - Usuario {s.chat_user.user_id}")
        print(f"   Tokens: {s.total_tokens}, Texto: {len(s.summary_text) if s.summary_text else 0} chars")
        if s.summary_text and len(s.summary_text) < 80:
            print(f"   Texto: \"{s.summary_text[:60]}...\"")
        print()
else:
    print("No hay resúmenes generados")

# 5. Detectar problemas comunes
print("\n[5] ANÁLISIS DE PROBLEMAS")
print("-" * 70)
issues = []

# Problema: Ollama no está conectando
try:
    requests.get(f'{ollama_url}/api/tags', timeout=5)
except Exception:
    issues.append("Ollama NO ESTÁ ACCESIBLE - No hay conexión al servidor")

# Problema: Resúmenes fallando con NO_DATA
fail_summaries = DailyTextSummary.objects.filter(has_data=False)
if fail_summaries.count() > 0:
    issues.append(f"Hay {fail_summaries.count()} resúmenes con NO_DATA (sin información)")

# Problema: Ejecuciones fallidas
failed_runs = SummaryExecutionControl.objects.filter(status='failed')
if failed_runs.count() > 0:
    issues.append(f"Hay {failed_runs.count()} corridas en estado FAILED")

# Problema: Sin datos recientes
if recent.exists():
    last_run = recent.first()
    hours_ago = (datetime.now(last_run.started_at.tzinfo) - last_run.started_at).total_seconds() / 3600
    if hours_ago > 24:
        issues.append(f"Última corrida fue hace {hours_ago:.1f} horas (scheduler no está corriendo)")

if not issues:
    print("✓ No se detectaron problemas")
else:
    for i, issue in enumerate(issues, 1):
        print(f"{i}. ⚠ {issue}")

print("\n" + "=" * 70)
