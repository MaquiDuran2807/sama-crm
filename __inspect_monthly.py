import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sama_core.settings")
django.setup()

from ingesta.models import MonthlyTextSummary

qs = MonthlyTextSummary.objects.filter(is_current=True, year=2026, month=4).select_related("user").order_by("user_id")
print("total=", qs.count())
for m in qs:
    label = m.user.name or m.user.phone_number or m.user.wa_id
    txt = (m.text or "").replace("\n", " ")[:140]
    print(f"user_id={m.user_id} | chat={label} | has_data={m.has_data} | rev={m.revision} | txt={txt}")
