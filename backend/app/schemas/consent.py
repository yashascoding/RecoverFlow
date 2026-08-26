from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.customer_email_consent import ConsentChannel, ConsentStatus


class ConsentCreate(BaseModel):
    customer_id: uuid.UUID
    channel: ConsentChannel
    source: str | None = Field(default=None)


class ConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    channel: ConsentChannel
    consent_status: ConsentStatus
    consented_at: datetime | None = None
    revoked_at: datetime | None = None
    source: str | None = None
    created_at: datetime
    updated_at: datetime


class ConsentOptOut(BaseModel):
    customer_id: uuid.UUID
    channel: ConsentChannel
