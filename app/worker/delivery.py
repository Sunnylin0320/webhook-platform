import httpx
from sqlalchemy.orm import Session

from app import models 


def build_payload(event: models.Event) -> dict:
    return {
        "id": str(event.id),
        "type": event.event_type,
        "created_at": event.created_at.isoformat(),
        "data": event.payload,
    }

def send_delivery(db: Session, delivery: models.Delivery) -> None:
    webhook = db.get(models.Webhook, delivery.webhook_id)
    event = db.get(models.Event, delivery.event_id)
    delivery.attempts += 1

    try:
        response = httpx.post(webhook.url, json=build_payload(event), timeout=5.0)
        if response.is_success:
            delivery.status = "succeeded"
            delivery.last_error = None
        else:
            delivery.status = "failed"
            delivery.last_error = f"HTTP {response.status_code}"
    except httpx.RequestError as exc:
        delivery.status = "failed"
        delivery.last_error = f"{type(exc).__name__}: {exc}"[:500]

    db.commit()