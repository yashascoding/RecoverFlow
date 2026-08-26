from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.recovery_attempt import RecoveryAttemptStatus, RecoveryChannel


class RecoveryAttemptCreate(BaseModel):
    customer_id: uuid.UUID
    payment_id: uuid.UUID
    channel: RecoveryChannel
    amount: int


class RecoveryAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    payment_id: uuid.UUID
    channel: RecoveryChannel
    status: RecoveryAttemptStatus
    attempt_number: int
    email_message_id: uuid.UUID | None = None
    recovery_link: str | None = None
    error_message: str | None = None
    metadata_: dict | None = Field(default=None, serialization_alias="metadata")
    sent_at: datetime | None = None
    opened_at: datetime | None = None
    clicked_at: datetime | None = None
    converted_at: datetime | None = None
    failed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RecoveryAttemptStatusUpdate(BaseModel):
    status: RecoveryAttemptStatus


class RecoveryAttemptListResponse(BaseModel):
    items: list[RecoveryAttemptResponse]
    total: int
    page: int
    page_size: int
    pages: int
