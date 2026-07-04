#!/usr/bin/env python
"""Muestra detalles del resumen generado en la prueba."""

import os
import sys

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sama_core.settings')
django.setup()

from ingesta.models import DailyTextSummary, SummaryExecutionControl

# Detalles de la corrida
log = SummaryExecutionControl.objects.get(run_key='test_user_521_1776411877.451508')
print('='*70)
print('EJECUCIÓN DE RESÚMENES (12h lookback)')
print('='*70)
print(f'Status: {log.status}')
print(f'Usuarios elegibles: {log.eligible_users}')
print(f'Usuarios procesados: {log.processed_users}')
print(f'Usuarios fallidos: {log.failed_users}')
print(f'Tokens generados:')
print(f'  - Prompt: {log.prompt_tokens}')
print(f'  - Completion: {log.completion_tokens}')
print(f'  - Total: {log.total_tokens}')
if log.detail:
    print(f'Detalle: {log.detail}')

# Resúmenes del usuario para hoy (04-16)
print('\n' + '='*70)
print('RESÚMENES GENERADOS (2026-04-16)')
print('='*70)
summaries = DailyTextSummary.objects.filter(summary_date='2026-04-16').order_by('id')
for s in summaries:
    print(f'\n📅 {s.summary_date}')
    print(f'   Tokens: {s.total_tokens} | has_data={s.has_data}')
    print(f'   Estado: {"✓ CON DATOS" if s.has_data else "✗ SIN DATOS"}')
    
    if s.text:
        print(f'   \n   📝 Resumen:\n   {s.text}')
    
    if s.pending_items:
        print(f'   \n   📋 Pendientes: {s.pending_items}')
    
    if s.mentioned_people:
        print(f'   \n   👥 Personas: {s.mentioned_people}')
    
    if s.payment_promises:
        print(f'   \n   💰 Pagos: {s.payment_promises}')
    
    if s.deadlines:
        print(f'   \n   📦 Entregas: {s.deadlines}')

print('\n' + '='*70)
print('✓ PRUEBA COMPLETADA EXITOSAMENTE')
print('='*70)
