"""Event worker — consumes events from Redis queue and processes them.

Usage:
    python -m app.workers.event_worker
"""
from __future__ import annotations

import asyncio
import signal
import sys

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.events.processor import EventProcessor
from app.events.queue import EventQueue, event_queue

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

# Graceful shutdown flag
_shutdown = asyncio.Event()


def _handle_signal(sig: int, frame: object) -> None:
    logger.info("shutdown_signal_received", extra={"signal": sig})
    _shutdown.set()


async def _register_handlers(processor: EventProcessor) -> None:
    """Register event handlers for each known event type."""
    from app.workers.handlers import HANDLERS

    for event_type, handler in HANDLERS.items():
        processor.register(event_type, handler)


async def _process_retry_queue(processor: EventProcessor, queue: EventQueue) -> None:
    """Periodically check the retry queue for events ready to be retried."""
    while not _shutdown.is_set():
        try:
            data = await queue.pop_retry(max_age_seconds=30)
            if data:
                await processor.process_one(data)
        except Exception as e:
            logger.error("retry_queue_error", extra={"error": str(e)})
        await asyncio.sleep(5)


async def run_worker() -> None:
    """Main worker loop — pop events from Redis and process them."""
    queue = event_queue
    processor = EventProcessor(queue)

    await _register_handlers(processor)

    logger.info(
        "worker_starting",
        extra={
            "redis_url": settings.REDIS_URL,
            "handlers": list(processor._handlers.keys()),
        },
    )

    # Run retry processor in background
    retry_task = asyncio.create_task(_process_retry_queue(processor, queue))

    try:
        while not _shutdown.is_set():
            try:
                data = await queue.pop(timeout=2)
                if data is None:
                    continue
                await processor.process_one(data)
            except Exception as e:
                logger.error("worker_loop_error", extra={"error": str(e)})
                await asyncio.sleep(1)
    finally:
        retry_task.cancel()
        try:
            await retry_task
        except asyncio.CancelledError:
            pass
        await queue.close()
        logger.info("worker_stopped")


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info("worker_process_started")
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("worker_interrupted")
    finally:
        logger.info("worker_process_exited")


if __name__ == "__main__":
    main()
