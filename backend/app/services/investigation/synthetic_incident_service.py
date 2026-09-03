from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.payment import Payment, PaymentStatus
from app.models.incident import Incident, IncidentStatus, IncidentSeverity
from app.services.investigation.investigation_service import InvestigationService
from app.schemas.investigation import InvestigationCreate

logger = get_logger(__name__)


class SyntheticIncidentService:
    """Service for creating synthetic test incidents."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.investigation_service = InvestigationService(db)

    async def create_upi_degradation_incident(
        self,
        affected_count: int = 50,
        revenue_impact: int = 2500000,
    ) -> dict:
        """Create a synthetic UPI degradation incident."""
        incident = Incident(
            title="Synthetic: UPI Payment Degradation",
            description=(
                "Simulated UPI payment degradation affecting multiple banks. "
                "This is a test incident for validating investigation pipeline."
            ),
            severity=IncidentSeverity.HIGH.value,
            incident_type="synthetic_upi_degradation",
            affected_payment_method="upi",
            revenue_at_risk=revenue_impact,
            failure_count=affected_count,
            baseline_failure_count=10.0,
            spike_threshold=30.0,
            detected_at=datetime.now(timezone.utc),
            status=IncidentStatus.OPEN.value,
            metadata_={
                "synthetic": True,
                "test_type": "upi_degradation",
                "affected_banks": ["HDFC", "ICICI", "SBI"],
                "affected_regions": ["South India", "West India"],
            },
        )
        self.db.add(incident)
        await self.db.flush()
        await self.db.refresh(incident)

        investigation_data = InvestigationCreate(
            incident_id=incident.id,
            title="Investigation: UPI Degradation",
            description="Investigating synthetic UPI degradation incident",
            metadata_={
                "synthetic": True,
                "test_type": "upi_degradation",
            },
        )
        investigation = await self.investigation_service.create_investigation(investigation_data)

        logger.info(
            "synthetic_upi_incident_created",
            extra={
                "incident_id": str(incident.id),
                "investigation_id": str(investigation.id),
                "affected_count": affected_count,
                "revenue_impact": revenue_impact,
            },
        )

        return {
            "incident_id": str(incident.id),
            "investigation_id": str(investigation.id),
            "type": "upi_degradation",
            "severity": "high",
            "affected_count": affected_count,
            "revenue_impact": revenue_impact,
            "affected_banks": ["HDFC", "ICICI", "SBI"],
            "affected_regions": ["South India", "West India"],
        }

    async def create_bank_decline_spike_incident(
        self,
        affected_bank: str = "HDFC",
        affected_count: int = 75,
        revenue_impact: int = 3750000,
    ) -> dict:
        """Create a synthetic bank decline spike incident."""
        incident = Incident(
            title=f"Synthetic: {affected_bank} Bank Decline Spike",
            description=(
                f"Simulated spike in payment declines from {affected_bank} bank. "
                "This is a test incident for validating investigation pipeline."
            ),
            severity=IncidentSeverity.CRITICAL.value,
            incident_type="synthetic_bank_decline_spike",
            affected_bank=affected_bank,
            revenue_at_risk=revenue_impact,
            failure_count=affected_count,
            baseline_failure_count=15.0,
            spike_threshold=50.0,
            detected_at=datetime.now(timezone.utc),
            status=IncidentStatus.OPEN.value,
            metadata_={
                "synthetic": True,
                "test_type": "bank_decline_spike",
                "bank": affected_bank,
                "decline_reason": "Do not honor",
                "affected_cards": ["Visa", "Mastercard"],
            },
        )
        self.db.add(incident)
        await self.db.flush()
        await self.db.refresh(incident)

        investigation_data = InvestigationCreate(
            incident_id=incident.id,
            title=f"Investigation: {affected_bank} Decline Spike",
            description=f"Investigating synthetic {affected_bank} decline spike",
            metadata_={
                "synthetic": True,
                "test_type": "bank_decline_spike",
                "bank": affected_bank,
            },
        )
        investigation = await self.investigation_service.create_investigation(investigation_data)

        logger.info(
            "synthetic_bank_decline_incident_created",
            extra={
                "incident_id": str(incident.id),
                "investigation_id": str(investigation.id),
                "bank": affected_bank,
                "affected_count": affected_count,
                "revenue_impact": revenue_impact,
            },
        )

        return {
            "incident_id": str(incident.id),
            "investigation_id": str(investigation.id),
            "type": "bank_decline_spike",
            "severity": "critical",
            "bank": affected_bank,
            "affected_count": affected_count,
            "revenue_impact": revenue_impact,
            "decline_reason": "Do not honor",
        }

    async def create_gateway_timeout_incident(
        self,
        affected_gateway: str = "Razorpay",
        affected_count: int = 100,
        revenue_impact: int = 5000000,
    ) -> dict:
        """Create a synthetic gateway timeout incident."""
        incident = Incident(
            title=f"Synthetic: {affected_gateway} Gateway Timeout",
            description=(
                f"Simulated timeout issues with {affected_gateway} payment gateway. "
                "This is a test incident for validating investigation pipeline."
            ),
            severity=IncidentSeverity.CRITICAL.value,
            incident_type="synthetic_gateway_timeout",
            affected_gateway=affected_gateway,
            revenue_at_risk=revenue_impact,
            failure_count=affected_count,
            baseline_failure_count=5.0,
            spike_threshold=20.0,
            detected_at=datetime.now(timezone.utc),
            status=IncidentStatus.OPEN.value,
            metadata_={
                "synthetic": True,
                "test_type": "gateway_timeout",
                "gateway": affected_gateway,
                "error_codes": ["GATEWAY_TIMEOUT", "SERVICE_UNAVAILABLE"],
                "affected_endpoints": ["/payments/create", "/payments/capture"],
            },
        )
        self.db.add(incident)
        await self.db.flush()
        await self.db.refresh(incident)

        investigation_data = InvestigationCreate(
            incident_id=incident.id,
            title=f"Investigation: {affected_gateway} Timeout",
            description=f"Investigating synthetic {affected_gateway} timeout",
            metadata_={
                "synthetic": True,
                "test_type": "gateway_timeout",
                "gateway": affected_gateway,
            },
        )
        investigation = await self.investigation_service.create_investigation(investigation_data)

        logger.info(
            "synthetic_gateway_timeout_incident_created",
            extra={
                "incident_id": str(incident.id),
                "investigation_id": str(investigation.id),
                "gateway": affected_gateway,
                "affected_count": affected_count,
                "revenue_impact": revenue_impact,
            },
        )

        return {
            "incident_id": str(incident.id),
            "investigation_id": str(investigation.id),
            "type": "gateway_timeout",
            "severity": "critical",
            "gateway": affected_gateway,
            "affected_count": affected_count,
            "revenue_impact": revenue_impact,
            "error_codes": ["GATEWAY_TIMEOUT", "SERVICE_UNAVAILABLE"],
        }

    async def run_all_synthetic_tests(self) -> dict:
        """Run all synthetic incident tests."""
        results = []

        upi_result = await self.create_upi_degradation_incident()
        results.append(upi_result)

        bank_result = await self.create_bank_decline_spike_incident()
        results.append(bank_result)

        gateway_result = await self.create_gateway_timeout_incident()
        results.append(gateway_result)

        return {
            "total_incidents_created": len(results),
            "incidents": results,
            "message": "All synthetic incidents created successfully",
        }
