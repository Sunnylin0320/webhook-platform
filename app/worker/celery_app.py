from celery import Celery

celery_app = Celery(
    "webhook_platform",
    broker="redis://localhost:6379/0",
    include=["app.worker.tasks"],
)
celery_app.conf.task_acks_late = True