import asyncio
import hashlib
import hmac
import json
import os
import random
import time
from collections import deque
from datetime import datetime

from fastapi import FastAPI, Request, Response

app = FastAPI(title="Fake customer endpoint")

SECRET = os.environ.get("WEBHOOK_SECRET")
TOLERANCE_SECONDS = 300

received = deque(maxlen=20)
seen_event_ids = set()

print(f"Signature verification: {'ON' if SECRET else 'OFF (set WEBHOOK_SECRET to enable)'}")


def verify_signature(raw_body: bytes, timestamp: str | None, signature: str | None) -> bool:
    if not timestamp or not signature:
        return False
    try:
        sent_at = int(timestamp)
    except ValueError:
        return False
    if abs(time.time() - sent_at) > TOLERANCE_SECONDS:
        return False
    signed_content = f"{timestamp}.".encode() + raw_body
    expected = hmac.new(SECRET.encode(), signed_content, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"v1={expected}", signature)


def record(result: str, body: dict, query: str) -> None:
    received.appendleft({
        "time": datetime.now().strftime("%H:%M:%S"),
        "result": result,
        "type": body.get("type"),
        "event_id": body.get("id"),
        "query": query,
    })
    print(f"[{result}] {body.get('type')} {body.get('id')}")


@app.post("/hooks")
async def receive(
    request: Request, fail_rate: float = 0.0, delay: float = 0.0, fail_status: int = 500
):
    raw_body = await request.body()
    body = json.loads(raw_body)
    query = request.url.query

    if SECRET and not verify_signature(
        raw_body,
        request.headers.get("webhook-timestamp"),
        request.headers.get("webhook-signature"),
    ):
        record("FAIL 401", body, query)
        return Response(status_code=401)

    if delay:
        await asyncio.sleep(delay)

    if random.random() < fail_rate:
        record(f"FAIL {fail_status}", body, query)
        return Response(status_code=fail_status)

    event_id = request.headers.get("webhook-id")
    if event_id in seen_event_ids:
        record("DUP", body, query)
        return {"received": True, "duplicate": True}

    seen_event_ids.add(event_id)
    record("OK", body, query)
    return {"received": True}


@app.get("/received")
def list_received():
    return list(received)