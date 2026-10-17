from app import models
from app.database import SessionLocal
from app.worker.celery_app import celery_app
from app.worker.delivery import send_delivery


@celery_app.task
def deliver(delivery_id: int) -> None:
    db = SessionLocal()
    try:
        delivery = db.get(models.Delivery, delivery_id)
        if delivery is None or delivery.status == "succeeded":
            return
        send_delivery(db, delivery)
    finally:
        db.close()