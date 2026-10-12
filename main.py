from fastapi import FastAPI
import models
from database import Base, engine
from webhooks import router as webhook_router
from events import router as event_router


Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(webhook_router)
app.include_router(event_router)

@app.get("/health")
def health():
    return {"status": "ok"}