from __future__ import annotations

import time


class RateLimiter:

    def __init__(self, delay_seconds: float = 2.0) -> None:
        if delay_seconds < 0:
            raise ValueError("delay_seconds cannot be negative")

        self.delay_seconds = delay_seconds
        self._last_request_time = 0.0

    def wait(self) -> None:
        current_time = time.time()
        elapsed = current_time - self._last_request_time

        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)

        self._last_request_time = time.time()