import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resumeit.settings')

app = Celery('resumeit')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
