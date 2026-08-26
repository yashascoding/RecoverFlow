from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.policy_decision import PolicyDecisionType, PolicyOutcome


class PolicyDecisionCreate(BaseModel):
    decision_type: PolicyDecisionType
    outcome: PolicyOutcome
    payment_id: uuid.UUID | None = Field(default=None)
    customer_id: uuid.UUID | None = Field(default=None)
    reason: str | None = Field(default=None)
    context: dict | None = Field(default=None)
    evaluated_by: str | None = Field(default=None)


class PolicyDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    decision_type: PolicyDecisionType
    outcome: PolicyOutcome
    payment_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    reason: str | None = None
    context: dict | None = None
    evaluated_by: str | None = None
    created_at: datetime
