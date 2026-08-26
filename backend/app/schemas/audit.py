from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.audit_log import AuditAction


class AuditLogCreate(BaseModel):
    actor: str | None = Field(default=None)
    action: AuditAction
    resource_type: str | None = Field(default=None)
    resource_id: uuid.UUID | None = Field(default=None)
    description: str | None = Field(default=None)
    payload: dict | None = Field(default=None)
    ip_address: str | None = Field(default=None)


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor: str | None = None
    action: AuditAction
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    description: str | None = None
    payload: dict | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime
