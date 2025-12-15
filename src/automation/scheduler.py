import asyncio
import time
from typing import Optional

from automation.utils.logger import get_logger

LOG = get_logger("scheduler")


class Scheduler:
    """
    A simple long-running loop that executes one task step at a configured interval,
    with backoff on failures.
    """

    def __init__(self, task, cfg: dict):
        self.task = task
        self.cfg = cfg
        self.interval_s = float(cfg["runtime"].get("poll_interval_seconds", 3.0))
        self.max_backoff_s = float(cfg["runtime"].get("max_backoff_seconds", 60.0))
        self.backoff_s = 0.0

    async def run(self, stop_event: asyncio.Event) -> None:
        await self.task.start()

        try:
            while not stop_event.is_set():
                t0 = time.perf_counter()
                try:
                    await self.task.step()
                    # Reset backoff on success
                    self.backoff_s = 0.0
                except Exception as e:
                    # Backoff on failures
                    self.backoff_s = min(self.max_backoff_s, (self.backoff_s * 2) if self.backoff_s else 2.0)
                    LOG.exception("Task step failed: %s. Backing off for %.1fs", e, self.backoff_s)

                elapsed = time.perf_counter() - t0
                sleep_for = max(0.0, self.interval_s - elapsed)

                # If we are backing off, extend the sleep.
                if self.backoff_s:
                    sleep_for = max(sleep_for, self.backoff_s)

                await asyncio.wait([stop_event.wait()], timeout=sleep_for)
        finally:
            await self.task.stop()
            LOG.info("Scheduler stopped.")
