import os

from celery import Celery

celery_app = Celery(
    "webhook_platform",
    broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    include=["app.worker.tasks"],
)
celery_app.conf.task_acks_late = True
celery_app.conf.beat_schedule = {
    "requeue-due-retries": {
        "task": "app.worker.tasks.requeue_due_retries",
        "schedule": 10.0,
    },
}