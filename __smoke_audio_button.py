import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sama_core.settings")

import django
django.setup()

from django.test import Client
import json
import time

client = Client(HTTP_HOST="localhost")

print("== AUDIO BUTTON SMOKE ==")

resp = client.post(
    "/ingesta/api/audio-briefing/",
    data=json.dumps({"instance_name": "Deya3", "team_user_id": None}),
    content_type="application/json",
)
print("trigger_status=", resp.status_code)
try:
    print("trigger_body_json=", resp.json())
except Exception:
    raw = resp.content.decode("utf-8", errors="ignore")
    print("trigger_body_text=", raw[:700])
if resp.status_code != 202:
    raise SystemExit(1)

payload = resp.json()
job_id = payload["job_id"]
print("job_id=", job_id)

last = None
for i in range(240):
    status_resp = client.get(f"/ingesta/api/sync/{job_id}/status/")
    if status_resp.status_code != 200:
        body = status_resp.content.decode("utf-8", errors="ignore")
        print("status_error=", status_resp.status_code, body[:700])
        raise SystemExit(2)

    data = status_resp.json()
    snapshot = (data.get("status"), data.get("progress"), data.get("message"))
    if snapshot != last:
        print("status=", snapshot)
        last = snapshot

    if data.get("status") in ("completed", "failed"):
        print("final=", json.dumps(data, ensure_ascii=False)[:4000])
        if data.get("status") != "completed":
            raise SystemExit(3)
        break

    time.sleep(0.5)
else:
    print("timeout_waiting_job")
    raise SystemExit(4)

print("SMOKE_OK")
