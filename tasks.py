import models
from celery_app import app
from database import SessionLocal
from delivery import send_delivery


@app.task
def deliver(delivery_id: int) -> None:
    db = SessionLocal()
    try:
        delivery = db.get(models.Delivery, delivery_id)
        if delivery is None or delivery.status == "succeeded":
            return
        send_delivery(db, delivery)
    finally:
        db.close()