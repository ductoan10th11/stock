"""Daily refresh after the market closes: new candles, model scores and paper-trading sessions."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timedelta

from app.services import paper_service, reports
from crawl import VN

logger = logging.getLogger("uvicorn.error")

REFRESH_AT = time(15, 30)
RETRY_DELAY_SECONDS = 600
MAX_ATTEMPTS = 3


def next_run(now: datetime) -> datetime:
    """The next weekday at REFRESH_AT strictly after `now`; exchange holidays just yield no new candles."""
    candidate = datetime.combine(now.date(), REFRESH_AT, tzinfo=now.tzinfo)
    while candidate <= now or candidate.weekday() >= 5:
        candidate = datetime.combine(candidate.date() + timedelta(days=1), REFRESH_AT, tzinfo=now.tzinfo)
    return candidate


async def refresh_loop() -> None:
    while True:
        now = datetime.now(VN)
        target = next_run(now)
        logger.info("next scheduled refresh at %s", target.isoformat(timespec="minutes"))
        await asyncio.sleep((target - now).total_seconds())
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                sessions = await asyncio.to_thread(paper_service.refresh)
                logger.info("scheduled refresh done, %d new sessions", sessions)
                sent = await asyncio.to_thread(reports.send_daily_report)
                logger.info("daily report %s", "sent" if sent else "skipped")
                break
            except Exception:
                logger.exception("scheduled refresh failed (attempt %d of %d)", attempt, MAX_ATTEMPTS)
                if attempt < MAX_ATTEMPTS:
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
