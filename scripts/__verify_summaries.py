#!/usr/bin/env python
"""Verifica que los resúmenes estén en la BD y visibles."""

import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sama_core.settings')
django.setup()

from ingesta.models import ChatUser, DailyTextSummary, MonthlyTextSummary

print("="*70)
print("VERIFICACIÓN DE RESÚMENES EN BASE DE DATOS")
print("="*70)

# Totales
daily_count = DailyTextSummary.objects.count()
monthly_count = MonthlyTextSummary.objects.count()

print(f"\nResúmenes diarios totales: {daily_count}")
print(f"Resúmenes mensuales totales: {monthly_count}")

# Por usuario - diarios
print("\n" + "="*70)
print("RESÚMENES DIARIOS POR USUARIO")
print("="*70)

daily_by_user = (
    DailyTextSummary.objects.values('user_id')
    .annotate(cnt=__import__('django.db.models', fromlist=['Count']).Count('id'))
    .order_by('-cnt')
)

for row in daily_by_user[:5]:
    user = ChatUser.objects.get(id=row['user_id'])
    count = row['cnt']
    summaries = DailyTextSummary.objects.filter(user_id=row['user_id']).order_by('-summary_date')[:3]
    print(f"\n{user.name or user.phone_number or user.wa_id} (ID={user.id}): {count} resúmenes")
    for s in summaries:
        status = "✓ CON DATOS" if s.has_data else "✗ SIN DATOS"
        print(f"  - {s.summary_date}: {status} ({s.total_tokens} tokens)")

# Por usuario - mensuales
print("\n" + "="*70)
print("RESÚMENES MENSUALES POR USUARIO")
print("="*70)

monthly_by_user = (
    MonthlyTextSummary.objects.values('user_id')
    .annotate(cnt=__import__('django.db.models', fromlist=['Count']).Count('id'))
    .order_by('-cnt')
)

for row in monthly_by_user[:5]:
    user = ChatUser.objects.get(id=row['user_id'])
    count = row['cnt']
    summaries = MonthlyTextSummary.objects.filter(user_id=row['user_id']).order_by('-year', '-month', '-revision')[:3]
    print(f"\n{user.name or user.phone_number or user.wa_id} (ID={user.id}): {count} resúmenes")
    for s in summaries:
        status = "✓ CON DATOS" if s.has_data else "✗ SIN DATOS"
        current = "(ACTUAL)" if s.is_current else ""
        print(f"  - {s.year}-{s.month:02d} r{s.revision}: {status} {current} ({s.total_tokens} tokens)")

print("\n" + "="*70)
print("✓ VERIFICACIóN COMPLETADA")
print("="*70)
print("\nPróximos pasos:")
print("1. Accede a /admin/ingesta/dailytextsummary/ para ver todos los resúmenes")
print("2. Accede a /ingesta/crm/user/[user_id]/ para verlos en el dashboard")
