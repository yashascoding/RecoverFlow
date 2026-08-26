from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.consent import ConsentCreate, ConsentOptOut, ConsentResponse
from app.services.consent.consent_service import ConsentService

router = APIRouter(prefix="/consent", tags=["consent"])


@router.post("/", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def opt_in_consent(
    body: ConsentCreate,
    db: AsyncSession = Depends(get_db),
) -> ConsentResponse:
    svc = ConsentService(db)
    consent = await svc.opt_in(
        customer_id=body.customer_id,
        channel=body.channel.value,
        source=body.source,
    )
    await db.commit()
    return ConsentResponse.model_validate(consent)


@router.post("/opt-out", response_model=ConsentResponse)
async def opt_out_consent(
    body: ConsentOptOut,
    db: AsyncSession = Depends(get_db),
) -> ConsentResponse:
    svc = ConsentService(db)
    consent = await svc.opt_out(
        customer_id=body.customer_id,
        channel=body.channel.value,
    )
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent record not found",
        )
    await db.commit()
    return ConsentResponse.model_validate(consent)


@router.get("/{customer_id}/{channel}", response_model=ConsentResponse)
async def get_consent_status(
    customer_id: uuid.UUID,
    channel: str,
    db: AsyncSession = Depends(get_db),
) -> ConsentResponse:
    svc = ConsentService(db)
    consent = await svc.get_consent(customer_id, channel)
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent not found",
        )
    return ConsentResponse.model_validate(consent)


@router.get("/{customer_id}", response_model=list[ConsentResponse])
async def list_customer_consents(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ConsentResponse]:
    from sqlalchemy import select

    from app.models.customer_email_consent import CustomerEmailConsent

    result = await db.execute(
        select(CustomerEmailConsent)
        .where(CustomerEmailConsent.customer_id == customer_id)
        .order_by(CustomerEmailConsent.created_at.desc())
    )
    consents = result.scalars().all()
    return [ConsentResponse.model_validate(c) for c in consents]
