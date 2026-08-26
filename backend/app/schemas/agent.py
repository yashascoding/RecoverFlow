from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.agent_action import AgentActionStatus, AgentActionType
from app.models.agent_run import AgentRunStatus, AgentType


class AgentRunCreate(BaseModel):
    agent_type: AgentType
    payment_id: uuid.UUID | None = Field(default=None)
    customer_id: uuid.UUID | None = Field(default=None)
    input_data: dict | None = Field(default=None)


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_type: AgentType
    status: AgentRunStatus
    payment_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    input_data: dict | None = None
    output_data: dict | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AgentActionCreate(BaseModel):
    run_id: uuid.UUID
    action_type: AgentActionType
    target: str | None = Field(default=None)
    payload: dict | None = Field(default=None)


class AgentActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    action_type: AgentActionType
    status: AgentActionStatus
    target: str | None = None
    payload: dict | None = None
    result: dict | None = None
    error_message: str | None = None
    executed_at: datetime | None = None
    created_at: datetime
