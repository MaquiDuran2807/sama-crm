import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sama_core.settings")
django.setup()

from ingesta.models import DailyTextSummary

rows = DailyTextSummary.objects.filter(user_id=532, summary_date__year=2026, summary_date__month=4).order_by("summary_date")
print("daily_count=", rows.count())
for d in rows:
    print("-" * 80)
    print("date=", d.summary_date)
    print("has_data=", d.has_data, "msgs=", d.source_message_count, "tokens=", d.total_tokens)
    print("text=", d.text)
    print("pending_items=", d.pending_items)
    print("mentioned_people=", d.mentioned_people)
    print("deadlines=", d.deadlines)
    print("payment_promises=", d.payment_promises)
