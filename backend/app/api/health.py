from __future__ import annotations

from datetime import datetime, timezone
import redis.asyncio as aioredis
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.database import engine
from app.schemas.payment import HealthResponse

router = APIRouter(tags=["health"])

settings = get_settings()

redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    postgres_status = "disconnected"
    redis_status = "disconnected"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        postgres_status = "connected"
    except Exception:
        pass

    try:
        await redis_client.ping()
        redis_status = "connected"
    except Exception:
        pass

    overall = "ok" if postgres_status == "connected" and redis_status == "connected" else "degraded"

    return HealthResponse(
        status=overall,
        postgres=postgres_status,
        redis=redis_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
