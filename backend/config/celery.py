import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("triagedock")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.beat_schedule = {
    "dispatch-pending-notifications": {
        "task": "incidents.process_due_deliveries",
        "schedule": 15.0,
    },
}
