from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.payment import PaymentStatus


class PaymentCreate(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in paise")
    currency: str = Field(default="INR", min_length=3, max_length=3)
    customer_email: EmailStr
    customer_phone: str | None = Field(default=None, max_length=20)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    razorpay_order_id: str
    razorpay_payment_id: str | None
    customer_email: str
    customer_phone: str | None
    amount: int
    currency: str
    status: PaymentStatus
    failure_reason: str | None = None
    recovery_email_sent: datetime | None
    recovery_email_opened: datetime | None
    payment_link_clicked: datetime | None
    original_payment_id: uuid.UUID | None
    metadata_: dict | None = None
    created_at: datetime
    updated_at: datetime


class PaymentListParams(BaseModel):
    status: PaymentStatus | None = None
    customer_email: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaymentListResponse(BaseModel):
    items: list[PaymentResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PaymentStatusUpdate(BaseModel):
    status: PaymentStatus
    failure_reason: str | None = None


class WebhookEventResponse(BaseModel):
    status: str = "received"
    event: str | None = None


class RecoveryStatusResponse(BaseModel):
    payment_id: uuid.UUID
    razorpay_order_id: str
    status: PaymentStatus
    recovery_email_sent: datetime | None
    recovery_email_opened: datetime | None
    payment_link_clicked: datetime | None
    recovery_attempts: int = 0


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    postgres: str
    redis: str
    timestamp: str
