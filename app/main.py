from fastapi import FastAPI

from app import models
from app.api.dashboard import router as dashboard_router
from app.api.events import router as event_router
from app.api.webhooks import router as webhook_router
from app.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(webhook_router)
app.include_router(event_router)
app.include_router(dashboard_router)


@app.get("/health")
def health():
    return {"status": "ok"}