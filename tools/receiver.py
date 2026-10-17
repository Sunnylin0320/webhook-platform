import asyncio
import random
from collections import deque
from datetime import datetime

from fastapi import FastAPI, Request, Response

app = FastAPI(title="Fake customer endpoint")

received = deque(maxlen=20)


@app.post("/hooks")
async def receive(
    request: Request, fail_rate: float = 0.0, delay: float = 0.0, fail_status: int = 500
):
    body = await request.json()
    if delay:
        await asyncio.sleep(delay)

    failed = random.random() < fail_rate
    result = f"FAIL {fail_status}" if failed else "OK"
    received.appendleft({
        "time": datetime.now().strftime("%H:%M:%S"),
        "result": result,
        "type": body.get("type"),
        "event_id": body.get("id"),
        "query": request.url.query,
    })
    print(f"[{result}] {body.get('type')} {body.get('id')}")

    if failed:
        return Response(status_code=fail_status)
    return {"received": True}


@app.get("/received")
def list_received():
    return list(received)