from fastapi import FastAPI
import models
from database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}