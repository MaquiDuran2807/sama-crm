import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sama_core.settings')
django.setup()

from django.conf import settings
from ingesta.models import Message

instance = 'Deya3'
url = f"{settings.EVOLUTION_BASE_URL.rstrip('/')}/chat/getBase64FromMediaMessage/{instance}"
headers = {'Content-Type': 'application/json'}
if settings.EVOLUTION_API_KEY:
    headers['apikey'] = settings.EVOLUTION_API_KEY

pending = Message.objects.filter(media_url__icontains='.enc', media_file='').order_by('-timestamp')[:40]
print('pending_sample=', pending.count())

ok = 0
nob64 = 0
httpfail = 0
exc = 0
for m in pending:
    raw = m.raw_data if isinstance(m.raw_data, dict) else {}
    try:
        r = requests.post(url, headers=headers, json={'message': raw}, timeout=25)
        text = (r.text or '').replace('\n', ' ')[:180]
        if r.status_code >= 400:
            httpfail += 1
            print('HTTP_FAIL', m.external_id, m.message_type, r.status_code, text)
            continue
        try:
            data = r.json()
        except Exception:
            data = {}
        b64 = str(data.get('base64') or '') if isinstance(data, dict) else ''
        if b64:
            ok += 1
            print('OK', m.external_id, m.message_type, data.get('mimetype'), data.get('fileName'))
        else:
            nob64 += 1
            print('NO_BASE64', m.external_id, m.message_type, text)
    except Exception as e:
        exc += 1
        print('EXC', m.external_id, m.message_type, type(e).__name__, str(e)[:140])

print('SUMMARY ok=', ok, 'nob64=', nob64, 'httpfail=', httpfail, 'exc=', exc)
