import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://webhook:webhook@localhost:5432/webhook_test"
)

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.database import Base, engine
    from app.main import app

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


class FakeTask:
    def __init__(self):
        self.calls = []

    def delay(self, delivery_id):
        self.calls.append(delivery_id)


@pytest.fixture
def enqueued(monkeypatch):
    from app.api import events

    fake = FakeTask()
    monkeypatch.setattr(events, "deliver", fake)
    return fake.calls