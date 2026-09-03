from __future__ import annotations

import uuid
from datetime import datetime, timezone
from math import ceil
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.alert import Alert, AlertStatus
from app.schemas.alert import (
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertListResponse,
    AlertTestResponse,
)

logger = get_logger(__name__)


class AlertService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_alert(self, data: AlertCreate) -> Alert:
        """Create a new alert."""
        alert = Alert(
            name=data.name,
            description=data.description,
            severity=data.severity,
            alert_type=data.alert_type,
            metric_name=data.metric_name,
            threshold_value=data.threshold_value,
            comparison_operator=data.comparison_operator,
            time_window_minutes=data.time_window_minutes,
            cooldown_minutes=data.cooldown_minutes,
            metadata_=data.metadata_,
            status=AlertStatus.ACTIVE.value,
        )
        self.db.add(alert)
        await self.db.flush()
        await self.db.refresh(alert)

        logger.info(
            "alert_created",
            extra={
                "alert_id": str(alert.id),
                "name": alert.name,
                "metric": alert.metric_name,
                "threshold": alert.threshold_value,
            },
        )
        return alert

    async def get_alert(self, alert_id: uuid.UUID) -> Alert | None:
        """Get an alert by ID."""
        result = await self.db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        return result.scalar_one_or_none()

    async def list_alerts(
        self,
        status: str | None = None,
        severity: str | None = None,
        alert_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AlertListResponse:
        """List alerts with optional filters."""
        query = select(Alert)
        count_query = select(func.count()).select_from(Alert)

        if status:
            query = query.where(Alert.status == status)
            count_query = count_query.where(Alert.status == status)
        if severity:
            query = query.where(Alert.severity == severity)
            count_query = count_query.where(Alert.severity == severity)
        if alert_type:
            query = query.where(Alert.alert_type == alert_type)
            count_query = count_query.where(Alert.alert_type == alert_type)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Alert.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return AlertListResponse(
            items=[AlertResponse.model_validate(a) for a in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if total else 0,
        )

    async def update_alert(
        self, alert_id: uuid.UUID, data: AlertUpdate
    ) -> Alert | None:
        """Update an alert."""
        alert = await self.get_alert(alert_id)
        if not alert:
            return None

        if data.name is not None:
            alert.name = data.name
        if data.description is not None:
            alert.description = data.description
        if data.status is not None:
            alert.status = data.status
        if data.severity is not None:
            alert.severity = data.severity
        if data.threshold_value is not None:
            alert.threshold_value = data.threshold_value
        if data.comparison_operator is not None:
            alert.comparison_operator = data.comparison_operator
        if data.time_window_minutes is not None:
            alert.time_window_minutes = data.time_window_minutes
        if data.cooldown_minutes is not None:
            alert.cooldown_minutes = data.cooldown_minutes
        if data.metadata_ is not None:
            alert.metadata_ = data.metadata_

        alert.updated_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(alert)

        logger.info(
            "alert_updated",
            extra={"alert_id": str(alert.id), "name": alert.name},
        )
        return alert

    async def test_alert(
        self, alert_id: uuid.UUID | None, metric_value: float
    ) -> AlertTestResponse:
        """Test if a metric value would trigger an alert."""
        if alert_id:
            alert = await self.get_alert(alert_id)
            if not alert:
                raise ValueError("Alert not found")
        else:
            alerts = await self.list_alerts(status="active", page_size=1)
            if not alerts.items:
                raise ValueError("No active alerts found")
            alert = alerts.items[0]

        would_trigger = self._evaluate_threshold(
            metric_value, alert.threshold_value, alert.comparison_operator
        )

        message = (
            f"Alert '{alert.name}' would {'trigger' if would_trigger else 'not trigger'} "
            f"with value {metric_value} {alert.comparison_operator} {alert.threshold_value}"
        )

        return AlertTestResponse(
            would_trigger=would_trigger,
            current_value=metric_value,
            threshold_value=alert.threshold_value,
            comparison_operator=alert.comparison_operator,
            alert_name=alert.name,
            message=message,
        )

    def _evaluate_threshold(
        self, value: float, threshold: float, operator: str
    ) -> bool:
        """Evaluate if a value exceeds a threshold based on the operator."""
        if operator == "gt":
            return value > threshold
        elif operator == "gte":
            return value >= threshold
        elif operator == "lt":
            return value < threshold
        elif operator == "lte":
            return value <= threshold
        elif operator == "eq":
            return value == threshold
        else:
            return False
