import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app import models
from app.database import SessionLocal
from app.worker.celery_app import celery_app
from app.worker.delivery import send_delivery

FAST_RETRIES = 5
FAST_BASE_SECONDS = 1
FAST_CAP_SECONDS = 16
SLOW_BASE_SECONDS = 60
SLOW_CAP_SECONDS = 3600
RETRY_WINDOW = timedelta(days=3)



def backoff_with_jitter(n: int, base: float, cap: float) -> float:
    delay = min(cap, base * 2 ** (n - 1))
    return random.uniform(delay / 2, delay)


@celery_app.task
def deliver(delivery_id: int) -> None:
    db = SessionLocal()
    retry_in = None
    try:
        delivery = db.get(models.Delivery, delivery_id)
        if delivery is None or delivery.status in ("succeeded", "dead"):
            return
        webhook = db.get(models.Webhook, delivery.webhook_id)
        event = db.get(models.Event, delivery.event_id)

        if webhook.status != "active":
            delivery.status = "dead"
            delivery.last_error = f"endpoint is {webhook.status}"
            db.commit()
            return

        delivery.attempts += 1
        result = send_delivery(webhook, event)

        if result.ok:
            delivery.status = "succeeded"
            delivery.last_error = None
            delivery.next_retry_at = None
        else:
            delivery.last_error = result.error
            retry_in = plan_retry(delivery, webhook, result.retryable)
        db.commit()
    finally:
        db.close()

    if retry_in is not None:
        deliver.apply_async((delivery_id,), countdown=retry_in)


def plan_retry(delivery: models.Delivery, webhook: models.Webhook, retryable: bool) -> float | None:
    now = datetime.now(timezone.utc)

    if not retryable:
        delivery.status = "dead"
        delivery.next_retry_at = None
        print(f"[DLQ] delivery {delivery.id}: non-retryable ({delivery.last_error})")
        return None

    if now - delivery.created_at > RETRY_WINDOW:
        delivery.status = "dead"
        delivery.next_retry_at = None
        webhook.status = "suspended"
        print(f"[DLQ] delivery {delivery.id}: gave up after {delivery.attempts} attempts")
        print(f"[NOTIFY] {webhook.user_id}: endpoint {webhook.url} has been suspended")
        return None

    delivery.status = "retrying"
    if delivery.attempts < FAST_RETRIES:
        delay = backoff_with_jitter(delivery.attempts, FAST_BASE_SECONDS, FAST_CAP_SECONDS)
        delivery.next_retry_at = None
        print(f"[RETRY] delivery {delivery.id}: attempt {delivery.attempts} failed, fast retry in {delay:.1f}s")
        return delay

    slow_n = delivery.attempts - FAST_RETRIES + 1
    delay = backoff_with_jitter(slow_n, SLOW_BASE_SECONDS, SLOW_CAP_SECONDS)
    delivery.next_retry_at = now + timedelta(seconds=delay)
    print(f"[RETRY] delivery {delivery.id}: attempt {delivery.attempts} failed, stored for retry in {delay:.1f}s")
    return None


@celery_app.task
def requeue_due_retries() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due = db.scalars(
            select(models.Delivery).where(
                models.Delivery.status == "retrying",
                models.Delivery.next_retry_at <= now,
            )
        ).all()
        due_ids = [delivery.id for delivery in due]
        for delivery in due:
            delivery.next_retry_at = None
        db.commit()
    finally:
        db.close()

    for delivery_id in due_ids:
        deliver.delay(delivery_id)