import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sama_core.settings")
django.setup()

from ingesta.models import MonthlyTextSummary
from ingesta.summary_service import TextSummaryService

service = TextSummaryService()
log = service.rebuild_monthly_summaries_from_daily(
    run_key="rebuild_monthly_valentina_2026_04_v2",
    force=True,
    user_id=532,
    year=2026,
    month=4,
)

m = MonthlyTextSummary.objects.filter(user_id=532, year=2026, month=4, is_current=True).first()
print("log_status=", log.status)
print("processed_users=", log.processed_users)
print("failed_users=", log.failed_users)
print("monthly_updated=", log.monthly_summaries_updated)
print("current_revision=", m.revision if m else None)
print("current_text=", (m.text if m else None))
