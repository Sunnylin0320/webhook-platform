from datetime import datetime
from typing import Literal
from pydantic import BaseModel, HttpUrl

class WebhookCreate(BaseModel):
    user_id: str
    event_type: str
    url: HttpUrl

class WebhookUpdate(BaseModel):
    url: HttpUrl | None = None
    status: Literal["active", "inactive"] | None = None

class WebhookOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: str
    event_type: str
    url: str
    status: str
    created_at: datetime
    updated_at: datetime

class WebhookCreated(WebhookOut):
    secret: str