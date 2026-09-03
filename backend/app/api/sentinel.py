from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.sentinel.sentinel_service import SentinelService

router = APIRouter(prefix="/sentinel", tags=["sentinel"])


@router.post("/run")
async def run_sentinel_check(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run a sentinel check to monitor metrics and trigger investigations."""
    svc = SentinelService(db)
    result = await svc.run_sentinel_check()
    return result.to_dict()


@router.get("/status")
async def get_sentinel_status(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the current sentinel status."""
    from app.services.alert.alert_service import AlertService
    from app.services.incident.incident_service import IncidentService

    alert_svc = AlertService(db)
    incident_svc = IncidentService(db)

    active_alerts = await alert_svc.list_alerts(status="active", page_size=1)
    incident_stats = await incident_svc.get_stats()

    return {
        "status": "active",
        "active_alerts": active_alerts.total,
        "open_incidents": incident_stats.open_incidents,
        "investigating_incidents": incident_stats.investigating_incidents,
        "total_revenue_at_risk": incident_stats.total_revenue_at_risk,
    }
