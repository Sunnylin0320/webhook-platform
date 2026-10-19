from datetime import datetime, timedelta, timezone

import pytest

from app import models
from app.worker.tasks import FAST_RETRIES, RETRY_WINDOW, backoff_with_jitter, plan_retry


def make_webhook():
    return models.Webhook(id=1, user_id="user_1", url="https://example.com/hook", status="active")


def make_delivery(attempts, age=timedelta(0)):
    return models.Delivery(
        id=1,
        attempts=attempts,
        status="pending",
        last_error="HTTP 500",
        created_at=datetime.now(timezone.utc) - age,
    )


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
def test_backoff_doubles_with_jitter(n):
    full_delay = min(16, 2 ** (n - 1))
    for _ in range(100):
        delay = backoff_with_jitter(n, base=1, cap=16)
        assert full_delay / 2 <= delay <= full_delay


def test_backoff_never_exceeds_cap():
    assert backoff_with_jitter(30, base=60, cap=3600) <= 3600


def test_non_retryable_error_goes_straight_to_dlq():
    delivery = make_delivery(attempts=1)
    webhook = make_webhook()

    retry_in = plan_retry(delivery, webhook, retryable=False)

    assert retry_in is None
    assert delivery.status == "dead"
    assert webhook.status == "active"


def test_early_failure_retries_quickly():
    delivery = make_delivery(attempts=1)

    retry_in = plan_retry(delivery, make_webhook(), retryable=True)

    assert delivery.status == "retrying"
    assert 0 < retry_in <= 1
    assert delivery.next_retry_at is None


def test_after_fast_retries_waits_in_database():
    delivery = make_delivery(attempts=FAST_RETRIES)

    retry_in = plan_retry(delivery, make_webhook(), retryable=True)

    assert retry_in is None
    assert delivery.status == "retrying"
    assert delivery.next_retry_at > datetime.now(timezone.utc)


def test_gives_up_after_retry_window_and_suspends_endpoint():
    delivery = make_delivery(attempts=20, age=RETRY_WINDOW + timedelta(minutes=1))
    webhook = make_webhook()

    retry_in = plan_retry(delivery, webhook, retryable=True)

    assert retry_in is None
    assert delivery.status == "dead"
    assert webhook.status == "suspended"