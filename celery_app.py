from celery import Celery

app = Celery(
    "webhook_platform",
    broker="redis://localhost:6379/0",
    include=["tasks"],
)
app.conf.task_acks_late = True