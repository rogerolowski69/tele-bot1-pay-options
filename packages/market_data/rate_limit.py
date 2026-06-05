import asyncio
import time


class AsyncRateLimiter:
    """Simple async rate limiter (max N calls per second)."""

    def __init__(self, max_per_second: float = 10.0):
        self._min_interval = 1.0 / max_per_second
        self._lock = asyncio.Lock()
        self._last_call = 0.0

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()
