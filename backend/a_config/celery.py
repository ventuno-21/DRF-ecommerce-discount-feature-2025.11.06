import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "a_config.settings")

app = Celery("a_config")

# Load broker URL and other configs from Django settings (we'll set them there)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in installed apps (looks for tasks.py)
app.autodiscover_tasks()
