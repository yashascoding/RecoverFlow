from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.alert import Alert, AlertStatus
from app.models.incident import Incident, IncidentStatus, IncidentSeverity
from app.models.payment import Payment, PaymentStatus
from app.services.alert.alert_service import AlertService
from app.services.incident.incident_service import IncidentService
from app.services.monitoring.transaction_monitoring_service import TransactionMonitoringService
from app.services.monitoring.spike_detection_service import SpikeDetectionService

logger = get_logger(__name__)


class SentinelResult:
    def __init__(
        self,
        *,
        alerts_checked: int,
        alerts_triggered: int,
        incidents_created: int,
        investigations_started: int,
        details: list[dict],
    ) -> None:
        self.alerts_checked = alerts_checked
        self.alerts_triggered = alerts_triggered
        self.incidents_created = incidents_created
        self.investigations_started = investigations_started
        self.details = details

    def to_dict(self) -> dict:
        return {
            "alerts_checked": self.alerts_checked,
            "alerts_triggered": self.alerts_triggered,
            "incidents_created": self.incidents_created,
            "investigations_started": self.investigations_started,
            "details": self.details,
        }


class SentinelService:
    """Sentinel service that monitors metrics and triggers investigations automatically."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.alert_svc = AlertService(db)
        self.incident_svc = IncidentService(db)
        self.monitoring_svc = TransactionMonitoringService(db)
        self.spike_svc = SpikeDetectionService(db)

    async def run_sentinel_check(self) -> SentinelResult:
        """Run a full sentinel check: evaluate alerts, create incidents, trigger investigations."""
        details = []
        alerts_triggered = 0
        incidents_created = 0
        investigations_started = 0

        active_alerts = await self.alert_svc.list_alerts(
            status=AlertStatus.ACTIVE.value, page_size=100
        )
        alerts_checked = active_alerts.total

        for alert in active_alerts.items:
            try:
                metric_value = await self._get_metric_value(alert.metric_name, alert.time_window_minutes)
                
                if metric_value is None:
                    continue

                would_trigger = self._evaluate_threshold(
                    metric_value, alert.threshold_value, alert.comparison_operator
                )

                if would_trigger:
                    if not self._is_in_cooldown(alert):
                        alerts_triggered += 1

                        incident = await self._create_incident_from_alert(alert, metric_value)
                        if incident:
                            incidents_created += 1

                            await self._trigger_investigation(incident, alert)
                            investigations_started += 1

                            alert.last_triggered_at = datetime.now(timezone.utc)
                            alert.last_value = metric_value
                            alert.status = AlertStatus.TRIGGERED.value
                            await self.db.flush()

                        details.append({
                            "alert_id": str(alert.id),
                            "alert_name": alert.name,
                            "metric_value": metric_value,
                            "threshold": alert.threshold_value,
                            "incident_created": incident is not None,
                            "message": f"Alert triggered: {alert.name}",
                        })
                    else:
                        details.append({
                            "alert_id": str(alert.id),
                            "alert_name": alert.name,
                            "metric_value": metric_value,
                            "threshold": alert.threshold_value,
                            "incident_created": False,
                            "message": f"Alert in cooldown: {alert.name}",
                        })

            except Exception as e:
                logger.error(
                    "sentinel_alert_check_error",
                    extra={"alert_id": str(alert.id), "error": str(e)},
                )
                details.append({
                    "alert_id": str(alert.id),
                    "alert_name": alert.name,
                    "error": str(e),
                    "message": f"Error checking alert: {alert.name}",
                })

        spikes_response = await self.spike_svc.detect_spikes(time_window_hours=1)
        if spikes_response.spikes_detected:
            for spike in spikes_response.spikes:
                incident = await self._create_incident_from_spike(spike)
                if incident:
                    incidents_created += 1
                    await self._trigger_investigation_from_spike(incident, spike)
                    investigations_started += 1

                    details.append({
                        "spike_type": spike.spike_type,
                        "dimension": spike.dimension,
                        "severity": spike.severity,
                        "incident_created": True,
                        "message": f"Incident created for spike: {spike.message}",
                    })

        logger.info(
            "sentinel_check_completed",
            extra={
                "alerts_checked": alerts_checked,
                "alerts_triggered": alerts_triggered,
                "incidents_created": incidents_created,
                "investigations_started": investigations_started,
            },
        )

        return SentinelResult(
            alerts_checked=alerts_checked,
            alerts_triggered=alerts_triggered,
            incidents_created=incidents_created,
            investigations_started=investigations_started,
            details=details,
        )

    async def _get_metric_value(self, metric_name: str, time_window_minutes: int) -> float | None:
        """Get the current value of a metric."""
        time_window_hours = max(time_window_minutes // 60, 1)
        metrics = await self.monitoring_svc.get_metrics(time_window_hours)

        if metric_name == "failure_rate":
            return metrics.failure_rate
        elif metric_name == "success_rate":
            return metrics.success_rate
        elif metric_name == "revenue_at_risk":
            return float(metrics.revenue_at_risk)
        elif metric_name == "recovered_revenue":
            return float(metrics.recovered_revenue)
        elif metric_name == "total_failures":
            return float(metrics.failed_transactions)
        else:
            return None

    def _evaluate_threshold(self, value: float, threshold: float, operator: str) -> bool:
        """Evaluate if a value exceeds a threshold."""
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
        return False

    def _is_in_cooldown(self, alert: Alert) -> bool:
        """Check if an alert is still in cooldown period."""
        if not alert.last_triggered_at:
            return False

        cooldown_end = alert.last_triggered_at + timedelta(minutes=alert.cooldown_minutes)
        return datetime.now(timezone.utc) < cooldown_end

    async def _create_incident_from_alert(
        self, alert: Alert, metric_value: float
    ) -> Incident | None:
        """Create an incident from a triggered alert."""
        from app.schemas.incident import IncidentCreate
        from datetime import timedelta

        severity_map = {
            "low": IncidentSeverity.LOW.value,
            "medium": IncidentSeverity.MEDIUM.value,
            "high": IncidentSeverity.HIGH.value,
            "critical": IncidentSeverity.CRITICAL.value,
        }

        title = f"Alert Triggered: {alert.name}"
        description = (
            f"Alert '{alert.name}' has been triggered.\n"
            f"Metric: {alert.metric_name}\n"
            f"Current Value: {metric_value}\n"
            f"Threshold: {alert.comparison_operator} {alert.threshold_value}\n"
            f"Time Window: {alert.time_window_minutes} minutes"
        )

        incident_data = IncidentCreate(
            title=title,
            description=description,
            severity=severity_map.get(alert.severity, IncidentSeverity.MEDIUM.value),
            incident_type="alert_triggered",
            revenue_at_risk=int(metric_value) if "revenue" in alert.metric_name else 0,
            failure_count=int(metric_value) if "failure" in alert.metric_name else 0,
            detected_at=datetime.now(timezone.utc),
            metadata_={
                "alert_id": str(alert.id),
                "metric_name": alert.metric_name,
                "metric_value": metric_value,
                "threshold": alert.threshold_value,
                "comparison_operator": alert.comparison_operator,
            },
        )

        return await self.incident_svc.create_incident(incident_data)

    async def _create_incident_from_spike(self, spike) -> Incident | None:
        """Create an incident from a detected spike."""
        from app.schemas.incident import IncidentCreate

        severity_map = {
            "low": IncidentSeverity.LOW.value,
            "medium": IncidentSeverity.MEDIUM.value,
            "high": IncidentSeverity.HIGH.value,
            "critical": IncidentSeverity.CRITICAL.value,
        }

        dimension_parts = spike.dimension.split(":", 1)
        dimension_type = dimension_parts[0] if len(dimension_parts) > 0 else "unknown"
        dimension_value = dimension_parts[1] if len(dimension_parts) > 1 else "unknown"

        incident_data = IncidentCreate(
            title=f"Spike Detected: {spike.spike_type}",
            description=spike.message,
            severity=severity_map.get(spike.severity, IncidentSeverity.MEDIUM.value),
            incident_type="spike_detected",
            affected_gateway=dimension_value if dimension_type == "gateway" else None,
            affected_bank=dimension_value if dimension_type == "bank" else None,
            affected_region=dimension_value if dimension_type == "region" else None,
            affected_payment_method=dimension_value if dimension_type == "payment_method" else None,
            failure_reason=dimension_value if dimension_type == "failure_reason" else None,
            revenue_at_risk=spike.revenue_impact,
            failure_count=spike.current_count,
            baseline_failure_count=spike.baseline_count,
            spike_threshold=spike.threshold,
            detected_at=spike.detected_at,
            metadata_={
                "spike_type": spike.spike_type,
                "dimension": spike.dimension,
                "current_count": spike.current_count,
                "baseline_count": spike.baseline_count,
                "threshold": spike.threshold,
            },
        )

        return await self.incident_svc.create_incident(incident_data)

    async def _trigger_investigation(self, incident: Incident, alert: Alert) -> None:
        """Trigger an investigation for an incident."""
        from app.services.agents.recovery_agent import RecoveryAgent

        try:
            agent = RecoveryAgent(self.db)
            result = await agent.run({
                "incident_id": str(incident.id),
                "incident_type": incident.incident_type,
                "severity": incident.severity,
                "alert_name": alert.name,
                "metric_name": alert.metric_name,
                "metric_value": alert.last_value,
                "investigation_type": "sentinel_triggered",
            })

            incident.status = IncidentStatus.INVESTIGATING.value
            incident.metadata_ = {
                **(incident.metadata_ or {}),
                "investigation_started": True,
                "agent_result": result,
            }
            await self.db.flush()

            logger.info(
                "investigation_triggered",
                extra={
                    "incident_id": str(incident.id),
                    "alert_name": alert.name,
                },
            )
        except Exception as e:
            logger.error(
                "investigation_trigger_failed",
                extra={"incident_id": str(incident.id), "error": str(e)},
            )

    async def _trigger_investigation_from_spike(self, incident: Incident, spike) -> None:
        """Trigger an investigation for a spike incident."""
        from app.services.agents.recovery_agent import RecoveryAgent

        try:
            agent = RecoveryAgent(self.db)
            result = await agent.run({
                "incident_id": str(incident.id),
                "incident_type": incident.incident_type,
                "severity": incident.severity,
                "spike_type": spike.spike_type,
                "dimension": spike.dimension,
                "current_count": spike.current_count,
                "baseline_count": spike.baseline_count,
                "investigation_type": "spike_detected",
            })

            incident.status = IncidentStatus.INVESTIGATING.value
            incident.metadata_ = {
                **(incident.metadata_ or {}),
                "investigation_started": True,
                "agent_result": result,
            }
            await self.db.flush()

            logger.info(
                "spike_investigation_triggered",
                extra={"incident_id": str(incident.id)},
            )
        except Exception as e:
            logger.error(
                "spike_investigation_trigger_failed",
                extra={"incident_id": str(incident.id), "error": str(e)},
            )
