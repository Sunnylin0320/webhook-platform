import httpx
import redis
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from pathlib import Path

from app import models
from app.database import get_db

router = APIRouter(tags=["dashboard"])

redis_client = redis.Redis.from_url("redis://localhost:6379/0")
RECEIVER_LOG_URL = "http://localhost:9000/received"
INDEX_HTML = Path(__file__).resolve().parent.parent / "static" / "index.html"


@router.get("/", include_in_schema=False)
def dashboard_page():
    return FileResponse(INDEX_HTML)


def get_queue_length() -> int | None:
    try:
        return redis_client.llen("celery")
    except redis.RedisError:
        return None


def get_receiver_log() -> list | None:
    try:
        return httpx.get(RECEIVER_LOG_URL, timeout=0.5).json()
    except httpx.HTTPError:
        return None


@router.get("/api/dashboard")
def dashboard_data(db: Session = Depends(get_db)):
    webhooks = db.scalars(select(models.Webhook).order_by(models.Webhook.id)).all()
    deliveries = db.scalars(
        select(models.Delivery).order_by(models.Delivery.id.desc()).limit(30)
    ).all()

    event_ids = {d.event_id for d in deliveries}
    events = db.scalars(select(models.Event).where(models.Event.id.in_(event_ids))).all()
    event_types = {e.id: e.event_type for e in events}
    webhook_urls = {w.id: w.url for w in webhooks}

    return {
        "queue_length": get_queue_length(),
        "receiver_log": get_receiver_log(),
        "webhooks": [
            {
                "id": w.id,
                "user_id": w.user_id,
                "event_type": w.event_type,
                "url": w.url,
                "status": w.status,
            }
            for w in webhooks
        ],
        "deliveries": [
            {
                "id": d.id,
                "event_id": str(d.event_id),
                "event_type": event_types.get(d.event_id),
                "webhook_id": d.webhook_id,
                "url": webhook_urls.get(d.webhook_id),
                "status": d.status,
                "attempts": d.attempts,
                "last_error": d.last_error,
                "next_retry_at": getattr(d, "next_retry_at", None),
            }
            for d in deliveries
        ],
    }