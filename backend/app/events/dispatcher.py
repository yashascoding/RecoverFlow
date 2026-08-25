from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any, Callable, Coroutine

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.database import async_session_factory
from app.events.queue import EventQueue, event_queue
from app.models.event import Event, EventStatus
from app.schemas.event import BaseEvent

logger = get_logger(__name__)

# Type alias for async event handlers
EventHandler = Callable[[BaseEvent], Coroutine[Any, Any, None]]


class EventBus:
    """Event dispatcher with DB persistence, duplicate detection, and Redis queue.

    Flow:
      1. Event arrives → check events table for duplicate event_id
      2. If duplicate → return DUPLICATE immediately
      3. If new → persist as PENDING in Postgres
      4. Push event to Redis queue for async worker consumption
      5. Worker processes and updates status to PROCESSED / FAILED
    """

    def __init__(self, queue: EventQueue | None = None) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._queue = queue or event_queue

    def on(self, event_type: str, handler: EventHandler) -> None:
        """Register an in-process handler for a given event type."""
        self._handlers[event_type].append(handler)

    def off(self, event_type: str, handler: EventHandler) -> None:
        """Remove a previously registered handler."""
        try:
            self._handlers[event_type].remove(handler)
        except ValueError:
            pass

    async def dispatch(self, event: BaseEvent, raw_payload: dict | None = None) -> EventStatus:
        """Persist event to Postgres, push to Redis queue.

        Args:
            event: The typed domain event.
            raw_payload: The original unparsed webhook body (e.g. full Razorpay JSON).

        Returns:
          - DUPLICATE if event_id already existed
          - PENDING   if event was persisted and queued for async processing
        """
        aggregate_id = self._extract_aggregate_id(event)

        async with async_session_factory() as db:
            # ── duplicate check ──────────────────────────────────────
            existing = await db.execute(
                select(Event).where(Event.event_id == event.event_id)
            )
            if existing.scalar_one_or_none() is not None:
                logger.info(
                    "event_duplicate_skipped",
                    extra={"event_id": str(event.event_id), "event_type": event.event_type},
                )
                return EventStatus.DUPLICATE

            # ── persist as pending ───────────────────────────────────
            db_event = Event(
                event_id=event.event_id,
                event_type=event.event_type,
                aggregate_id=aggregate_id,
                source=event.source.value,
                payload=event.model_dump(mode="json"),
                raw_payload=raw_payload,
                status=EventStatus.PENDING.value,
            )
            db.add(db_event)
            await db.commit()

        # ── push to Redis queue ──────────────────────────────────────
        await self._queue.push(
            event_id=event.event_id,
            event_type=event.event_type,
            payload=event.model_dump(mode="json"),
        )

        # ── run in-process handlers (optional, for same-process consumers) ──
        in_process_handlers = self._handlers.get(event.event_type, [])
        if in_process_handlers:
            import asyncio
            results = await asyncio.gather(
                *(self._safe_call(h, event) for h in in_process_handlers),
                return_exceptions=True,
            )
            for result in results:
                if isinstance(result, Exception):
                    logger.error(
                        "in_process_handler_error",
                        extra={"event_type": event.event_type, "error": str(result)},
                    )

        logger.info(
            "event_dispatched",
            extra={
                "event_id": str(event.event_id),
                "event_type": event.event_type,
                "status": EventStatus.PENDING.value,
            },
        )
        return EventStatus.PENDING

    async def _safe_call(self, handler: EventHandler, event: BaseEvent) -> None:
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                "event_handler_exception",
                extra={"handler": handler.__qualname__, "event_type": event.event_type, "error": str(e)},
            )
            raise

    @staticmethod
    def _extract_aggregate_id(event: BaseEvent) -> uuid.UUID | None:
        """Pull the primary entity ID from the event payload."""
        payload = getattr(event, "payload", None)
        if payload is None:
            return None
        for field in ("payment_id", "message_id", "customer_id"):
            val = getattr(payload, field, None)
            if val is not None:
                return val
        return None


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
event_bus = EventBus()
