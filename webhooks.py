import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

router = APIRouter(prefix="/v1/webhook", tags=["webhooks"])

def get_or_404(db: Session, webhook_id: int) -> models.Webhook:
    webhook = db.get(models.Webhook, webhook_id)
    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


@router.post("", response_model=schemas.WebhookCreated, status_code=201)
def create_webhook(body: schemas.WebhookCreate, db: Session = Depends(get_db)):
    webhook = models.Webhook(
        user_id=body.user_id,
        event_type=body.event_type,
        url=str(body.url),
        secret=secrets.token_hex(32),
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


@router.get("/{webhook_id}", response_model=schemas.WebhookOut)
def read_webhook(webhook_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, webhook_id)


@router.put("/{webhook_id}", response_model=schemas.WebhookOut)
def update_webhook(
    webhook_id: int, body: schemas.WebhookUpdate, db: Session = Depends(get_db)
):
    webhook = get_or_404(db, webhook_id)
    if body.url is not None:
        webhook.url = str(body.url)
    if body.status is not None:
        webhook.status = body.status
    db.commit()
    db.refresh(webhook)
    return webhook


@router.delete("/{webhook_id}", status_code=204)
def delete_webhook(webhook_id: int, db: Session = Depends(get_db)):
    webhook = get_or_404(db, webhook_id)
    db.delete(webhook)
    db.commit()