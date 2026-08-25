from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.database import async_session_factory
from app.events.queue import EventQueue
from app.models.event import Event, EventStatus

logger = get_logger(__name__)

# Type for event handler functions
EventHandler = Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]


class EventProcessor:
    """Processes events from the Redis queue, updates DB status, handles retries."""

    def __init__(self, queue: EventQueue) -> None:
        self._queue = queue
        self._handlers: dict[str, EventHandler] = {}

    def register(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        self._handlers[event_type] = handler
        logger.info("handler_registered", extra={"event_type": event_type})

    async def process_one(self, data: dict[str, Any]) -> bool:
        """Process a single event from the queue.

        Returns True if processed successfully, False otherwise.
        """
        event_id = uuid.UUID(data["event_id"])
        event_type = data["event_type"]
        payload = data["payload"]

        # Mark as processing in DB
        async with async_session_factory() as db:
            result = await db.execute(
                select(Event).where(Event.event_id == event_id)
            )
            db_event = result.scalar_one_or_none()
            if db_event:
                db_event.status = EventStatus.PROCESSING.value
                await db.commit()

        # Find and run handler
        handler = self._handlers.get(event_type)
        if handler is None:
            logger.warning("no_handler_for_event", extra={"event_type": event_type})
            await self._ack_success(event_id)
            return True

        try:
            await handler(event_type, payload)
            await self._ack_success(event_id)
            return True
        except Exception as e:
            logger.error(
                "event_processing_failed",
                extra={"event_id": str(event_id), "event_type": event_type, "error": str(e)},
            )
            await self._handle_failure(event_id, event_type, payload, str(e))
            return False

    async def _ack_success(self, event_id: uuid.UUID) -> None:
        """Mark event as processed and ack from queue."""
        async with async_session_factory() as db:
            result = await db.execute(
                select(Event).where(Event.event_id == event_id)
            )
            db_event = result.scalar_one_or_none()
            if db_event:
                db_event.status = EventStatus.PROCESSED.value
                db_event.processed_at = datetime.now(timezone.utc)
                await db.commit()
        await self._queue.ack(event_id)

    async def _handle_failure(
        self,
        event_id: uuid.UUID,
        event_type: str,
        payload: dict[str, Any],
        error: str,
    ) -> None:
        """Handle a failed event: increment retry count, retry or dead-letter."""
        async with async_session_factory() as db:
            result = await db.execute(
                select(Event).where(Event.event_id == event_id)
            )
            db_event = result.scalar_one_or_none()
            if not db_event:
                return

            db_event.retry_count += 1
            db_event.last_error = error

            if db_event.retry_count >= db_event.max_retries:
                db_event.status = EventStatus.FAILED.value
                await db.commit()
                await self._queue.dead_letter(event_id, event_type, payload)
                logger.warning(
                    "event_max_retries_exceeded",
                    extra={
                        "event_id": str(event_id),
                        "retry_count": db_event.retry_count,
                    },
                )
            else:
                db_event.status = EventStatus.PENDING.value
                await db.commit()
                await self._queue.retry(event_id, event_type, payload)
                logger.info(
                    "event_scheduled_for_retry",
                    extra={
                        "event_id": str(event_id),
                        "retry_count": db_event.retry_count,
                        "max_retries": db_event.max_retries,
                    },
                )
