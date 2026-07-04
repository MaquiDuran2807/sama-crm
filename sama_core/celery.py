import os
from celery import Celery

# Establecer las configuraciones de Django por defecto para Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sama_core.settings.development')

app = Celery('sama_core')

# Usar una cadena aquí significa que el worker no tiene que serializar
# el objeto de configuración a los procesos hijos.
# - namespace='CELERY' significa que todas las claves de configuración
#   relacionadas con Celery deben tener el prefijo 'CELERY_'.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descubrir tareas automáticamente en todas las apps Django registradas
app.autodiscover_tasks()
