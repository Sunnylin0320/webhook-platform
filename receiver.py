import asyncio
import random
from fastapi import FastAPI, Request, Response

app = FastAPI(title="Fake customer endpoint")


@app.post("/hooks")
async def receive(request: Request, fail_rate: float = 0.0, delay: float = 0.0):
    body = await request.json()
    if delay:
        await asyncio.sleep(delay)
    if random.random() < fail_rate:
        print(f"[FAIL] {body['type']} {body['id']}")
        return Response(status_code=500)
    print(f"[OK]   {body['type']} {body['id']}")
    return {"received": True}