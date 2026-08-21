from fastapi import APIRouter
from sqlalchemy import text
import redis.asyncio as redis
from datetime import datetime

from app.core.config import settings
from app.db.session import engine

router = APIRouter()

REDIS_URL = settings.REDIS_URL or f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

@router.get("/health")
async def health_check():

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        postgres_status = "connected"
    except Exception as e:
        postgres_status = "disconnected"

    try:
        await redis_client.ping()
        redis_status = "connected"
    except Exception as e:
        redis_status = "disconnected"

    return {
        "status": "ok" if postgres_status == "connected" and redis_status == "connected"
            else "degraded",
        "postgres": postgres_status,
        "redis": redis_status,
        "timestamp": datetime.utcnow().isoformat()
    }
