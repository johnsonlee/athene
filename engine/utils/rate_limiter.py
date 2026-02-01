"""Simple rate limiter for yfinance API calls."""

import time
from engine.config import RATE_LIMIT_PAUSE


class RateLimiter:
    """Enforces a minimum pause between calls."""

    def __init__(self, pause: float = RATE_LIMIT_PAUSE):
        self._pause = pause
        self._last_call = 0.0

    def wait(self) -> None:
        elapsed = time.time() - self._last_call
        if elapsed < self._pause:
            time.sleep(self._pause - elapsed)
        self._last_call = time.time()


rate_limiter = RateLimiter()
