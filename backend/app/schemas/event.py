from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Event source identifiers
# ---------------------------------------------------------------------------
class EventSource(str, Enum):
    WEBHOOK = "webhook"
    API = "api"
    SYSTEM = "system"
    AGENT = "agent"
    WORKER = "worker"


# ---------------------------------------------------------------------------
# Base event — every domain event shares these fields
# ---------------------------------------------------------------------------
class BaseEvent(BaseModel):
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique event ID")
    event_type: str = Field(..., description="Dot-separated event type, e.g. payment.created")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when the event occurred",
    )
    source: EventSource = Field(..., description="Subsystem that emitted the event")
    version: int = Field(default=1, description="Schema version for backward compat")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary extra data")
    dedup_key: str | None = Field(default=None, description="Business-level dedup key for duplicate detection")


# ---------------------------------------------------------------------------
# Payment events
# ---------------------------------------------------------------------------
class PaymentEventPayload(BaseModel):
    payment_id: uuid.UUID
    razorpay_order_id: str
    razorpay_payment_id: str | None = None
    customer_id: uuid.UUID | None = None
    customer_email: str
    amount: int = Field(description="Amount in paise")
    currency: str = "INR"
    status: str


class PaymentCreatedEvent(BaseEvent):
    event_type: Literal["payment.created"] = "payment.created"
    payload: PaymentEventPayload


class PaymentAuthorizedEvent(BaseEvent):
    event_type: Literal["payment.authorized"] = "payment.authorized"
    payload: PaymentEventPayload


class PaymentCapturedEvent(BaseEvent):
    event_type: Literal["payment.captured"] = "payment.captured"
    payload: PaymentEventPayload


class PaymentFailedEvent(BaseEvent):
    event_type: Literal["payment.failed"] = "payment.failed"
    payload: PaymentEventPayload
    failure_reason: str | None = None


class PaymentRefundedEvent(BaseEvent):
    event_type: Literal["payment.refunded"] = "payment.refunded"
    payload: PaymentEventPayload
    refund_amount: int | None = Field(default=None, description="Refund amount in paise")


# ---------------------------------------------------------------------------
# Email events
# ---------------------------------------------------------------------------
class EmailEventPayload(BaseModel):
    message_id: uuid.UUID
    customer_id: uuid.UUID
    recipient_email: str
    template_id: uuid.UUID | None = None
    subject: str | None = None
    provider_message_id: str | None = None


class EmailMessageReceivedEvent(BaseEvent):
    event_type: Literal["email.message.received"] = "email.message.received"
    payload: EmailEventPayload
    direction: Literal["inbound"] = "inbound"
    raw_headers: dict[str, str] | None = None


class EmailMessageSentEvent(BaseEvent):
    event_type: Literal["email.message.sent"] = "email.message.sent"
    payload: EmailEventPayload
    direction: Literal["outbound"] = "outbound"


class EmailDeliveredEvent(BaseEvent):
    event_type: Literal["email.delivered"] = "email.delivered"
    payload: EmailEventPayload


class EmailOpenedEvent(BaseEvent):
    event_type: Literal["email.opened"] = "email.opened"
    payload: EmailEventPayload


class EmailBouncedEvent(BaseEvent):
    event_type: Literal["email.bounced"] = "email.bounced"
    payload: EmailEventPayload
    bounce_reason: str | None = None


class EmailComplainedEvent(BaseEvent):
    event_type: Literal["email.complained"] = "email.complained"
    payload: EmailEventPayload


# ---------------------------------------------------------------------------
# Union type for all events (useful for type-hinting dispatchers)
# ---------------------------------------------------------------------------
DomainEvent = (
    PaymentCreatedEvent
    | PaymentAuthorizedEvent
    | PaymentCapturedEvent
    | PaymentFailedEvent
    | PaymentRefundedEvent
    | EmailMessageReceivedEvent
    | EmailMessageSentEvent
    | EmailDeliveredEvent
    | EmailOpenedEvent
    | EmailBouncedEvent
    | EmailComplainedEvent
)
