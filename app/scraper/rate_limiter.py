"""
Rate limiter for OutreachIQ acquisition layer.

Enforces a randomized delay between successive requests to pace
acquisition responsibly.  This is NOT an anti-bot evasion mechanism;
it exists to avoid hammering permitted data sources.

Usage::

    limiter = RateLimiter(min_delay_seconds=1.5, max_delay_seconds=3.0)
    limiter.wait()   # called before each acquisition
"""

from __future__ import annotations

import logging
import random
import time

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Configurable rate limiter with a randomized delay window.

    Args:
        min_delay_seconds: Minimum seconds to wait between requests.
        max_delay_seconds: Maximum seconds to wait between requests.
                           Must be >= min_delay_seconds.

    The first call to wait() does not sleep if no prior request has
    been tracked (i.e., the elapsed time already exceeds the target).

    Uses time.monotonic() for elapsed-time measurement, which is
    immune to wall-clock adjustments.
    """

    def __init__(
        self,
        min_delay_seconds: float = 1.5,
        max_delay_seconds: float = 3.0,
        # Legacy single-value alias kept for backward compatibility:
        delay_seconds: float | None = None,
    ) -> None:
        # Backward-compat: if caller uses old delay_seconds= kwarg, map it
        if delay_seconds is not None:
            min_delay_seconds = delay_seconds
            max_delay_seconds = delay_seconds

        if min_delay_seconds < 0:
            raise ValueError("min_delay_seconds cannot be negative")
        if max_delay_seconds < min_delay_seconds:
            raise ValueError(
                "max_delay_seconds must be >= min_delay_seconds"
            )

        self.min_delay_seconds = min_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        # Initialized to 0.0 so the first call does not sleep
        self._last_request_time: float = 0.0

    def wait(self) -> None:
        """
        Block for the remaining time required since the last call.

        The delay is randomized between min_delay_seconds and
        max_delay_seconds.  Only the portion of the delay that has
        not already elapsed is slept.
        """
        target = random.uniform(self.min_delay_seconds, self.max_delay_seconds)
        now = time.monotonic()
        elapsed = now - self._last_request_time
        remaining = target - elapsed

        if remaining > 0:
            logger.debug(
                "Rate limiter sleeping %.2f s (target=%.2f s, elapsed=%.2f s)",
                remaining,
                target,
                elapsed,
            )
            time.sleep(remaining)

        self._last_request_time = time.monotonic()