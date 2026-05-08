import os
from datetime import timedelta

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sama_core.settings")
django.setup()

from ingesta.models import (ChatUser, DailyTextSummary, Message,
                            MonthlyTextSummary)

USER_ID = 532
YEAR = 2026
MONTH = 4

user = ChatUser.objects.get(pk=USER_ID)
label = user.name or user.phone_number or user.wa_id
print(f"Chat validado: {label} (user_id={USER_ID})")
print("=" * 100)

messages = list(
    Message.objects.filter(user_id=USER_ID, timestamp__year=YEAR, timestamp__month=MONTH, message_type=Message.MessageType.TEXT)
    .order_by("timestamp")
)
media_messages = list(
    Message.objects.filter(
        user_id=USER_ID,
        timestamp__year=YEAR,
        timestamp__month=MONTH,
        message_type__in=[Message.MessageType.AUDIO, Message.MessageType.IMAGE, Message.MessageType.VIDEO],
    ).order_by("timestamp")
)
messages = sorted(messages + media_messages, key=lambda m: m.timestamp)
print(f"Mensajes de texto en {YEAR}-{MONTH:02d}: {len(messages)}")
print("\n[Timeline ordenado por timestamp]")

pending_client_ts = None
for msg in messages:
    role = "EQUIPO" if msg.from_me else "CLIENTE"
    content = (msg.content or "").replace("\n", " ").strip()
    media_label = ""
    if msg.message_type == Message.MessageType.AUDIO:
        media_label = "[AUDIO]"
    elif msg.message_type == Message.MessageType.IMAGE:
        media_label = "[IMAGEN]"
    elif msg.message_type == Message.MessageType.VIDEO:
        media_label = "[VIDEO]"
    if media_label and content:
        content = f"{media_label} {content}"
    elif media_label and not content:
        content = media_label
    if len(content) > 120:
        content = content[:117] + "..."

    response_note = ""
    if msg.from_me and pending_client_ts is not None:
        delta = msg.timestamp - pending_client_ts
        response_note = f" | RESPUESTA_A_CLIENTE en {delta}"
        pending_client_ts = None
    elif not msg.from_me:
        pending_client_ts = msg.timestamp

    print(f"{msg.timestamp.isoformat()} | {role:7} | {content}{response_note}")

if pending_client_ts is not None:
    print(f"\nPendiente sin respuesta de equipo desde: {pending_client_ts.isoformat()}")

print("\n" + "=" * 100)
print("[Diarios usados para construir mensual]")
daily_rows = list(
    DailyTextSummary.objects.filter(user_id=USER_ID, summary_date__year=YEAR, summary_date__month=MONTH)
    .order_by("summary_date")
)
print(f"Cantidad de diarios: {len(daily_rows)}")
for d in daily_rows:
    summary = (d.text or "").replace("\n", " ")
    if len(summary) > 180:
        summary = summary[:177] + "..."
    print(
        f"dia={d.summary_date} | has_data={d.has_data} | msgs={d.source_message_count} | "
        f"tokens={d.total_tokens} | resumen={summary}"
    )

print("\n[Mensual actual]")
monthly = MonthlyTextSummary.objects.filter(user_id=USER_ID, year=YEAR, month=MONTH, is_current=True).order_by("-revision").first()
if monthly:
    print(
        f"revision={monthly.revision} | has_data={monthly.has_data} | msgs_base={monthly.source_message_count} | "
        f"tokens={monthly.total_tokens}"
    )
    print("texto:")
    print(monthly.text or "NO_DATA")
else:
    print("NO_DATA")
