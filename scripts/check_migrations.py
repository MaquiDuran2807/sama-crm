import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sama_core.settings')
django.setup()

from django.db import connection
with connection.cursor() as c:
    c.execute("SELECT app, name FROM django_migrations ORDER BY id")
    for row in c.fetchall():
        print(row)