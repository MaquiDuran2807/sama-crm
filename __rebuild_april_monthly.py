import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sama_core.settings")
django.setup()

from ingesta.summary_service import TextSummaryService

service = TextSummaryService()
log = service.rebuild_monthly_summaries_from_daily(
    run_key="rebuild_monthly_from_daily_2026_04_clean",
    force=True,
    year=2026,
    month=4,
)

print("status=", log.status)
print("processed_users=", log.processed_users)
print("failed_users=", log.failed_users)
print("monthly_created=", log.monthly_summaries_created)
print("monthly_updated=", log.monthly_summaries_updated)
print("tokens=", log.total_tokens)
print("detail=", log.detail)
