import asyncio
import logging

from app.services.job_manager import JobManager

logger = logging.getLogger(__name__)


async def cleanup_loop(manager: JobManager, ttl_minutes: int, interval_seconds: int) -> None:
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            await manager.cleanup_expired(ttl_minutes)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Download cleanup pass failed")
