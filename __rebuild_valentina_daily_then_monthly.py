import os
from datetime import datetime

import django
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sama_core.settings")
django.setup()

from ingesta.models import MonthlyTextSummary
from ingesta.summary_service import TextSummaryService

service = TextSummaryService()
tz = timezone.now().tzinfo
start = datetime(2026, 4, 1, 0, 0, 0, tzinfo=tz)
end = datetime(2026, 5, 1, 0, 0, 0, tzinfo=tz)

log_daily = service.run_for_slot(
    slot_start=start,
    slot_end=end,
    run_key="rebuild_daily_valentina_2026_04",
    force=True,
    user_ids=[532],
)
print("daily_run_status=", log_daily.status)
print("daily_processed_users=", log_daily.processed_users)
print("daily_tokens=", log_daily.total_tokens)

log_monthly = service.rebuild_monthly_summaries_from_daily(
    run_key="rebuild_monthly_valentina_2026_04_after_daily",
    force=True,
    user_id=532,
    year=2026,
    month=4,
)
print("monthly_run_status=", log_monthly.status)
print("monthly_processed_users=", log_monthly.processed_users)
print("monthly_tokens=", log_monthly.total_tokens)

m = MonthlyTextSummary.objects.filter(user_id=532, year=2026, month=4, is_current=True).order_by("-revision").first()
print("current_revision=", m.revision if m else None)
print("current_has_data=", m.has_data if m else None)
print("current_text=", (m.text if m else None))
