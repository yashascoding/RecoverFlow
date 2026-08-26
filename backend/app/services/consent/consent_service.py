from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.customer_email_consent import (
    ConsentChannel,
    ConsentStatus,
    CustomerEmailConsent,
)

logger = get_logger(__name__)


class ConsentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def opt_in(
        self,
        customer_id: uuid.UUID,
        channel: str,
        source: str | None = None,
    ) -> CustomerEmailConsent:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(CustomerEmailConsent).where(
                CustomerEmailConsent.customer_id == customer_id,
                CustomerEmailConsent.channel == channel,
            )
        )
        consent = result.scalar_one_or_none()

        if consent:
            consent.consent_status = ConsentStatus.GRANTED.value
            consent.consented_at = now
            consent.revoked_at = None
            consent.source = source
            consent.updated_at = now
        else:
            consent = CustomerEmailConsent(
                customer_id=customer_id,
                channel=channel,
                consent_status=ConsentStatus.GRANTED.value,
                consented_at=now,
                source=source,
            )
            self.db.add(consent)

        await self.db.flush()
        await self.db.refresh(consent)
        logger.info(
            "consent_opt_in",
            extra={"customer_id": str(customer_id), "channel": channel},
        )
        return consent

    async def opt_out(
        self,
        customer_id: uuid.UUID,
        channel: str,
    ) -> CustomerEmailConsent | None:
        result = await self.db.execute(
            select(CustomerEmailConsent).where(
                CustomerEmailConsent.customer_id == customer_id,
                CustomerEmailConsent.channel == channel,
            )
        )
        consent = result.scalar_one_or_none()

        if not consent:
            logger.warning(
                "consent_not_found_for_opt_out",
                extra={"customer_id": str(customer_id), "channel": channel},
            )
            return None

        now = datetime.now(timezone.utc)
        consent.consent_status = ConsentStatus.REVOKED.value
        consent.revoked_at = now
        consent.updated_at = now
        await self.db.flush()
        logger.info(
            "consent_opt_out",
            extra={"customer_id": str(customer_id), "channel": channel},
        )
        return consent

    async def get_consent(
        self,
        customer_id: uuid.UUID,
        channel: str,
    ) -> CustomerEmailConsent | None:
        result = await self.db.execute(
            select(CustomerEmailConsent).where(
                CustomerEmailConsent.customer_id == customer_id,
                CustomerEmailConsent.channel == channel,
            )
        )
        return result.scalar_one_or_none()

    async def has_consent(self, customer_id: uuid.UUID, channel: str) -> bool:
        consent = await self.get_consent(customer_id, channel)
        return consent is not None

    async def validate_consent(self, customer_id: uuid.UUID, channel: str) -> bool:
        consent = await self.get_consent(customer_id, channel)
        if not consent:
            return False
        return consent.consent_status == ConsentStatus.GRANTED.value
