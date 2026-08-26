from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerCreate(BaseModel):
    email: EmailStr
    name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    status: str = Field(default="active", pattern="^(active|inactive|blocked)$")


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    status: str | None = Field(default=None, pattern="^(active|inactive|blocked)$")


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str | None
    phone: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class CustomerListResponse(BaseModel):
    items: list[CustomerResponse]
    total: int
    page: int
    page_size: int
    pages: int
