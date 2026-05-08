import os
import json
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sama_core.settings')
django.setup()

from django.conf import settings
from ingesta.models import Message

INSTANCE = 'Deya3'
LIMIT = 30

headers = {'Content-Type': 'application/json'}
if settings.EVOLUTION_API_KEY:
    headers['apikey'] = settings.EVOLUTION_API_KEY

url = f"{settings.EVOLUTION_BASE_URL.rstrip('/')}/chat/getBase64FromMediaMessage/{INSTANCE}"

qs = Message.objects.filter(message_type='audio', media_url__icontains='.enc', media_file='').order_by('-timestamp')[:LIMIT]
print('testing', qs.count(), 'messages at', url)

ok = 0
fail = 0
for m in qs:
    raw = m.raw_data if isinstance(m.raw_data, dict) else {}
    try:
        r = requests.post(url, headers=headers, json={'message': raw}, timeout=25)
        text = (r.text or '').replace('\n', ' ')[:220]
        if r.status_code < 400:
            data = r.json() if 'application/json' in (r.headers.get('Content-Type') or '') else {}
            b64 = str(data.get('base64') or '') if isinstance(data, dict) else ''
            if b64:
                ok += 1
                print('[OK]', m.external_id, 'status=', r.status_code, 'mime=', data.get('mimetype'), 'file=', data.get('fileName'))
            else:
                fail += 1
                print('[FAIL-NOBASE64]', m.external_id, 'status=', r.status_code, 'resp=', text)
        else:
            fail += 1
            print('[FAIL-HTTP]', m.external_id, 'status=', r.status_code, 'resp=', text)
    except Exception as exc:
        fail += 1
        print('[FAIL-EXC]', m.external_id, type(exc).__name__, str(exc)[:180])

print('summary ok=', ok, 'fail=', fail)
