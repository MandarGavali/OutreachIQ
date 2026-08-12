"""
Lightweight in-memory profile cache with TTL for OutreachIQ V2.

Avoids re-acquiring the same profile within a configurable time window.
Uses the normalized profile URL as the cache key.

Design constraints:
  - In-process only (no Redis, no database).
  - Does NOT cache credentials, cookies, or session state.
  - Failed acquisitions must NOT be cached (callers must not call set()
    on error paths).
  - Bounded by max_size to prevent unbounded growth.

Usage::

    cache = ProfileCache(ttl_seconds=300, max_size=100)
    profile = cache.get("https://linkedin.com/in/jane-doe")
    if profile is None:
        profile = acquire(...)
        cache.set("https://linkedin.com/in/jane-doe", profile)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from app.models.profile_models import ScrapedProfile

logger = logging.getLogger(__name__)

_DEFAULT_TTL = 300        # 5 minutes
_DEFAULT_MAX_SIZE = 100


@dataclass
class _CacheEntry:
    profile: ScrapedProfile
    expires_at: float  # monotonic timestamp


class ProfileCache:
    """
    Thread-unsafe in-memory cache suitable for single-process use.

    Args:
        ttl_seconds: How long a cached profile remains valid.
        max_size: Maximum number of profiles to keep in memory.
                  When the cache is full, the oldest entry is evicted.
    """

    def __init__(
        self,
        ttl_seconds: float = _DEFAULT_TTL,
        max_size: int = _DEFAULT_MAX_SIZE,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be > 0")
        if max_size <= 0:
            raise ValueError("max_size must be > 0")
        self._ttl = ttl_seconds
        self._max_size = max_size
        # Insertion-ordered dict for simple FIFO eviction
        self._store: dict[str, _CacheEntry] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, profile_url: str) -> ScrapedProfile | None:
        """
        Return a cached profile or None if absent / expired.

        Expired entries are removed on access (lazy eviction).
        """
        key = normalize_profile_url(profile_url)
        entry = self._store.get(key)
        if entry is None:
            logger.debug("Cache miss for %s", key)
            return None
        if time.monotonic() > entry.expires_at:
            logger.debug("Cache expired for %s", key)
            del self._store[key]
            return None
        logger.debug("Cache hit for %s", key)
        return entry.profile

    def set(self, profile_url: str, profile: ScrapedProfile) -> None:
        """
        Store a profile in the cache.

        Evicts the oldest entry if the cache is at capacity.
        """
        key = normalize_profile_url(profile_url)
        if len(self._store) >= self._max_size and key not in self._store:
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]
            logger.debug("Cache evicted oldest entry: %s", oldest_key)

        self._store[key] = _CacheEntry(
            profile=profile,
            expires_at=time.monotonic() + self._ttl,
        )
        logger.debug("Cached profile for %s (ttl=%.0f s)", key, self._ttl)

    def invalidate(self, profile_url: str) -> None:
        """Remove a specific entry from the cache."""
        key = normalize_profile_url(profile_url)
        removed = self._store.pop(key, None)
        if removed is not None:
            logger.debug("Cache invalidated for %s", key)

    def clear(self) -> None:
        """Remove all entries (useful in tests)."""
        self._store.clear()

    def __len__(self) -> int:
        """Return current number of stored entries (may include expired)."""
        return len(self._store)


# ---------------------------------------------------------------------------
# URL normalizer (shared by cache and acquisition layer)
# ---------------------------------------------------------------------------

def normalize_profile_url(url: str) -> str:
    """
    Normalize a profile URL for use as a stable cache key.

    Rules:
    - Strip leading/trailing whitespace
    - Strip a trailing slash (LinkedIn URLs are path-based; trailing /
      is semantically irrelevant)
    - Lowercase the scheme and host (but NOT the path, which is
      case-sensitive on some platforms)

    Args:
        url: A raw profile URL string.

    Returns:
        Normalized URL string.
    """
    url = url.strip().rstrip("/")
    # Lowercase only scheme://host portion
    if "://" in url:
        scheme, rest = url.split("://", 1)
        if "/" in rest:
            host, path = rest.split("/", 1)
            url = f"{scheme.lower()}://{host.lower()}/{path}"
        else:
            url = f"{scheme.lower()}://{rest.lower()}"
    return url
