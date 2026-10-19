from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.worker.tasks import deliver

router = APIRouter(prefix="/v1/events", tags=["events"])


@router.post("", response_model=schemas.EventAccepted, status_code=202)
def publish_event(body: schemas.EventCreate, db: Session = Depends(get_db)):
    event = models.Event(
        user_id=body.user_id,
        event_type=body.event_type,
        payload=body.payload,
    )
    db.add(event)
    db.flush()

    webhooks = db.scalars(
        select(models.Webhook).where(
            models.Webhook.user_id == body.user_id,
            models.Webhook.event_type == body.event_type,
            models.Webhook.status == "active",
        )
    ).all()


    deliveries = [
    models.Delivery(event_id=event.id, webhook_id=webhook.id)
    for webhook in webhooks
    ]
    db.add_all(deliveries)
    db.commit()

    for delivery in deliveries:
        deliver.delay(delivery.id)

    return {"event_id": event.id, "deliveries_created": len(deliveries)}