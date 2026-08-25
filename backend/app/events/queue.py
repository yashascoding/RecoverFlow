from __future__ import annotations

import json
import uuid
from typing import Any

import redis.asyncio as redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Queue names
EVENT_QUEUE = "recoverflow:events:pending"
RETRY_QUEUE = "recoverflow:events:retry"
DEAD_LETTER_QUEUE = "recoverflow:events:dead_letter"
PROCESSING_SET = "recoverflow:events:processing"


class EventQueue:
    """Redis-backed event queue using reliable list pattern (LPUSH + BRPOP).

    Queues:
      - pending:      main intake queue
      - retry:        failed events awaiting retry (sorted by timestamp)
      - dead_letter:  events that exhausted all retries
      - processing:   set of event_ids currently being processed
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or settings.REDIS_URL
        self._pool: redis.ConnectionPool | None = None
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        if self._client is None:
            self._pool = redis.ConnectionPool.from_url(
                self._redis_url, decode_responses=True
            )
            self._client = redis.Redis(connection_pool=self._pool)
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
            self._pool = None

    # ── Push ────────────────────────────────────────────────────────────

    async def push(self, event_id: uuid.UUID, event_type: str, payload: dict[str, Any]) -> None:
        """Push an event onto the pending queue."""
        client = await self._get_client()
        message = json.dumps({
            "event_id": str(event_id),
            "event_type": event_type,
            "payload": payload,
        })
        await client.lpush(EVENT_QUEUE, message)
        logger.info(
            "event_queued",
            extra={"event_id": str(event_id), "event_type": event_type},
        )

    # ── Consume ─────────────────────────────────────────────────────────

    async def pop(self, timeout: int = 5) -> dict[str, Any] | None:
        """Blocking pop from the pending queue. Returns None on timeout."""
        client = await self._get_client()
        result = await client.brpop(EVENT_QUEUE, timeout=timeout)
        if result is None:
            return None
        _queue_name, raw = result
        data = json.loads(raw)

        # Mark as processing
        await client.sadd(PROCESSING_SET, data["event_id"])
        logger.info(
            "event_popped",
            extra={"event_id": data["event_id"], "event_type": data["event_type"]},
        )
        return data

    async def ack(self, event_id: uuid.UUID) -> None:
        """Acknowledge successful processing — remove from processing set."""
        client = await self._get_client()
        await client.srem(PROCESSING_SET, str(event_id))
        logger.info("event_acked", extra={"event_id": str(event_id)})

    # ── Retry ───────────────────────────────────────────────────────────

    async def retry(self, event_id: uuid.UUID, event_type: str, payload: dict[str, Any]) -> None:
        """Move a failed event to the retry queue."""
        client = await self._get_client()
        await client.srem(PROCESSING_SET, str(event_id))
        message = json.dumps({
            "event_id": str(event_id),
            "event_type": event_type,
            "payload": payload,
        })
        # Use ZADD with timestamp as score for ordered retry
        import time
        score = time.time()
        await client.zadd(RETRY_QUEUE, {message: score})
        logger.info("event_requeued", extra={"event_id": str(event_id)})

    async def pop_retry(self, max_age_seconds: int = 3600) -> dict[str, Any] | None:
        """Pop the oldest retryable event if it's old enough to retry."""
        client = await self._get_client()
        import time
        now = time.time()
        cutoff = now - max_age_seconds
        # Get events with score <= now (ready to retry)
        results = await client.zrangebyscore(
            RETRY_QUEUE, "-inf", now, start=0, num=1, withscores=True
        )
        if not results:
            return None
        raw, score = results[0]
        # Remove from sorted set
        await client.zrem(RETRY_QUEUE, raw)
        data = json.loads(raw)
        await client.sadd(PROCESSING_SET, data["event_id"])
        return data

    # ── Dead Letter ─────────────────────────────────────────────────────

    async def dead_letter(self, event_id: uuid.UUID, event_type: str, payload: dict[str, Any]) -> None:
        """Move an event to the dead letter queue after max retries."""
        client = await self._get_client()
        await client.srem(PROCESSING_SET, str(event_id))
        message = json.dumps({
            "event_id": str(event_id),
            "event_type": event_type,
            "payload": payload,
        })
        await client.lpush(DEAD_LETTER_QUEUE, message)
        logger.warning("event_dead_lettered", extra={"event_id": str(event_id)})

    # ── Inspection ──────────────────────────────────────────────────────

    async def queue_lengths(self) -> dict[str, int]:
        """Return current lengths of all queues."""
        client = await self._get_client()
        return {
            "pending": await client.llen(EVENT_QUEUE),
            "retry": await client.zcard(RETRY_QUEUE),
            "processing": await client.scard(PROCESSING_SET),
            "dead_letter": await client.llen(DEAD_LETTER_QUEUE),
        }


# Module-level singleton
event_queue = EventQueue()
