#!/usr/bin/env python
"""Diagnostica por qué no se generaron resúmenes."""

import os
from datetime import timedelta

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sama_core.settings')
django.setup()

from django.utils import timezone

from ingesta.models import (ChatUser, DailyTextSummary, Message,
                            SummaryExecutionControl)

print("="*70)
print("DIAGNÓSTICO: ¿POR QUÉ NO SE GENERARON RESÚMENES?")
print("="*70)

# Última ejecución
last_run = SummaryExecutionControl.objects.order_by('-started_at').first()
slot_start = last_run.slot_start
slot_end = last_run.slot_end

print(f"\nÚltima ejecución: {last_run.run_key}")
print(f"Slot: {slot_start.isoformat()} a {slot_end.isoformat()}")
print(f"Status: {last_run.status}")
print(f"Usuarios procesados: {last_run.processed_users}/{last_run.eligible_users}")

# Mensajes de texto en la ventana
print(f"\n" + "="*70)
print("MENSAJES DE TEXTO EN VENTANA DE RESUMEN")
print("="*70)

text_msgs_in_slot = Message.objects.filter(
    message_type=Message.MessageType.TEXT,
    timestamp__gte=slot_start,
    timestamp__lt=slot_end
)

print(f"Total: {text_msgs_in_slot.count()}")

# Por usuario
from django.db.models import Count

by_user = text_msgs_in_slot.values('user_id').annotate(cnt=Count('id')).order_by('-cnt')
print(f"\nPor usuario:")
for row in by_user:
    user = ChatUser.objects.get(id=row['user_id'])
    print(f"  - {user.name or user.phone_number or user.wa_id} ({user.id}): {row['cnt']} msgs")

# Usuarios elegibles
print(f"\n" + "="*70)
print("USUARIOS ELEGIBLES PARA RESUMEN")
print("="*70)

text_message_types = [Message.MessageType.TEXT]
eligible_users = ChatUser.objects.filter(
    messages__message_type__in=text_message_types,
    messages__timestamp__gte=slot_start,
    messages__timestamp__lt=slot_end
).distinct()

print(f"Total: {eligible_users.count()}")
for user in eligible_users:
    msgs = text_msgs_in_slot.filter(user=user).count()
    print(f"  - {user.name or user.phone_number or user.wa_id} ({user.id}): {msgs} msgs")
    
    # Ver si ya tiene resúmenes para esas fechas
    dates = set()
    for msg in text_msgs_in_slot.filter(user=user):
        dates.add(msg.timestamp.date())
    
    existing_summaries = DailyTextSummary.objects.filter(
        user=user,
        summary_date__in=dates
    )
    print(f"    Resúmenes existentes para {len(dates)} días: {existing_summaries.count()}")

print("\n" + "="*70)
print("CONCLUSIÓN")
print("="*70)

if text_msgs_in_slot.count() == 0:
    print("❌ NO HAY MENSAJES DE TEXTO en esta ventana")
    print("   → No hay datos para procesar")
elif eligible_users.count() == 0:
    print("❌ NO HAY USUARIOS ELEGIBLES")
    print("   → Algo salió mal en el filtro")
else:
    print("⚠️ Hay mensajes pero potencialmente:")
    print("   1. Todos los usuarios ya tienen resúmenes sin cambios")
    print("   2. El deduplicador evitó reprocesar (behavior normal)")
