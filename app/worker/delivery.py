from dataclasses import dataclass

import httpx

from app import models


@dataclass
class SendResult:
    ok: bool
    retryable: bool
    error: str | None = None


def build_payload(event: models.Event) -> dict:
    return {
        "id": str(event.id),
        "type": event.event_type,
        "created_at": event.created_at.isoformat(),
        "data": event.payload,
    }


def is_retryable_status(status_code: int) -> bool:
    return status_code >= 500 or status_code in (408, 429)


def send_delivery(webhook: models.Webhook, event: models.Event) -> SendResult:
    try:
        response = httpx.post(webhook.url, json=build_payload(event), timeout=5.0)
    except httpx.RequestError as exc:
        return SendResult(ok=False, retryable=True, error=f"{type(exc).__name__}: {exc}"[:500])

    if response.is_success:
        return SendResult(ok=True, retryable=False)
    return SendResult(
        ok=False,
        retryable=is_retryable_status(response.status_code),
        error=f"HTTP {response.status_code}",
    )