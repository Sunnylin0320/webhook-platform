from dataclasses import dataclass
import httpx
import hashlib
import hmac
import json
import time
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

def sign(secret: str, timestamp: int, body: bytes) -> str:
    signed_content = f"{timestamp}.".encode() + body
    digest = hmac.new(secret.encode(), signed_content, hashlib.sha256).hexdigest()
    return f"v1={digest}"


def is_retryable_status(status_code: int) -> bool:
    return status_code >= 500 or status_code in (408, 429)


def send_delivery(webhook: models.Webhook, event: models.Event) -> SendResult:
    body = json.dumps(build_payload(event), separators=(",", ":")).encode()
    timestamp = int(time.time())
    headers = {
        "Content-Type": "application/json",
        "Webhook-Id": str(event.id),
        "Webhook-Timestamp": str(timestamp),
        "Webhook-Signature": sign(webhook.secret, timestamp, body),
    }

    try:
        response = httpx.post(webhook.url, content=body, headers=headers, timeout=5.0)
    except httpx.RequestError as exc:
        return SendResult(ok=False, retryable=True, error=f"{type(exc).__name__}: {exc}"[:500])

    if response.is_success:
        return SendResult(ok=True, retryable=False)
    return SendResult(
        ok=False,
        retryable=is_retryable_status(response.status_code),
        error=f"HTTP {response.status_code}",
    )