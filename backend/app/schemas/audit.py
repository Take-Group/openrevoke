import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ApiModel


class AuditEventOut(ApiModel):
    id: uuid.UUID
    at: datetime
    actor: str
    event: str
    entity_type: str
    entity_id: uuid.UUID | None
    data: dict[str, Any] | None
    app_id: uuid.UUID | None = Field(description="App the event is about, when there is one")
    person_id: uuid.UUID | None = Field(description="Person the event is about, when there is one")


class AuditEventPage(BaseModel):
    items: list[AuditEventOut]
    total: int
