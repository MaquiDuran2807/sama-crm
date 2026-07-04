import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sama_core.settings')
django.setup()

from ingesta.models import SummaryExecutionControl

run_key = 'reset_daily_2026-04-01_2026-04-18'
log = SummaryExecutionControl.objects.filter(run_key=run_key).first()

if not log:
    print('NO_LOG')
    raise SystemExit(0)

print('run_key=', log.run_key)
print('status=', log.status)
print('processed=', log.processed_users, '/', log.eligible_users)
print('started_at=', log.started_at)
print('finished_at=', log.finished_at)
if log.started_at and log.finished_at:
    delta = log.finished_at - log.started_at
    secs = int(delta.total_seconds())
    print('duration_seconds=', secs)
    print('duration_minutes=', round(secs / 60, 2))
    print('duration_hms=', delta)
print('prompt_tokens=', log.prompt_tokens)
print('completion_tokens=', log.completion_tokens)
print('total_tokens=', log.total_tokens)
print('daily_created=', log.daily_summaries_created)
print('daily_updated=', log.daily_summaries_updated)
