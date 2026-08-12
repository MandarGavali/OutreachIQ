"""
ProfileScraper — V2 orchestrator for the full acquisition pipeline.

Ties together:
  1. URL validation
  2. Cache lookup
  3. Rate limiting
  4. Acquisition adapter
  5. Normalization → ScrapedProfile
  6. Cache population

The scrape_profile() function (legacy V1 API) is preserved unchanged
so existing callers and tests continue to work without modification.

New callers should use ProfileScraper directly for dependency
injection and testability.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.models.profile_models import ScrapedProfile
from app.scraper.acquisition import ProfileAcquisition
from app.scraper.cache import ProfileCache, normalize_profile_url
from app.scraper.exceptions import ProfileAcquisitionError
from app.scraper.normalizer import normalize_profile
from app.scraper.parser import parse_profile
from app.scraper.rate_limiter import RateLimiter
from app.scraper.url_validator import InvalidProfileURLError, validate_profile_url

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Batch protection
# ---------------------------------------------------------------------------

MAX_BATCH_SIZE: int = settings.PROFILE_MAX_BATCH_SIZE


def validate_batch_size(urls: list[str]) -> None:
    """
    Reject batches that exceed the configured maximum.

    Args:
        urls: List of profile URLs requested.

    Raises:
        ValueError: If the batch is too large.
    """
    if len(urls) > MAX_BATCH_SIZE:
        raise ValueError(
            f"Batch size {len(urls)} exceeds the maximum of {MAX_BATCH_SIZE}. "
            "Split your request into smaller batches."
        )


# ---------------------------------------------------------------------------
# ProfileScraper — injectable, testable orchestrator
# ---------------------------------------------------------------------------

class ProfileScraper:
    """
    End-to-end profile acquisition orchestrator.

    Args:
        acquisition: An object that satisfies the ProfileAcquisition
                     protocol (fixture adapter, text adapter, or a
                     future real-data adapter).
        rate_limiter: RateLimiter to pace requests.
        cache: Optional ProfileCache.  Pass None to disable caching.

    Example::

        from app.scraper.adapters import FixtureProfileAdapter
        from app.scraper.cache import ProfileCache
        from app.scraper.rate_limiter import RateLimiter

        adapter = FixtureProfileAdapter()
        scraper = ProfileScraper(
            acquisition=adapter,
            rate_limiter=RateLimiter(min_delay_seconds=0, max_delay_seconds=0),
            cache=ProfileCache(ttl_seconds=60),
        )
        profile = scraper.scrape(profile_url="https://linkedin.com/in/jane")
    """

    def __init__(
        self,
        acquisition: ProfileAcquisition,
        rate_limiter: RateLimiter,
        cache: ProfileCache | None = None,
    ) -> None:
        self._acquisition = acquisition
        self._rate_limiter = rate_limiter
        self._cache = cache

    def scrape(self, profile_url: str) -> ScrapedProfile:
        """
        Run the full acquisition pipeline for a single profile URL.

        Args:
            profile_url: Profile URL to acquire and normalize.

        Returns:
            Canonical ScrapedProfile.

        Raises:
            InvalidProfileURLError: Bad URL.
            ProfileNotFoundError: Profile does not exist.
            ProfileTimeoutError: Acquisition timed out.
            ProfileValidationError: Data failed normalization.
            ProfileAcquisitionError: Any other acquisition failure.
        """
        # 1. Validate URL
        validated_url = validate_profile_url(profile_url)
        normalized_key = normalize_profile_url(validated_url)

        logger.info("Profile acquisition started for %s", normalized_key)

        # 2. Cache check
        if self._cache is not None:
            cached = self._cache.get(normalized_key)
            if cached is not None:
                logger.info("Cache hit — returning cached profile for %s", normalized_key)
                return cached
            logger.debug("Cache miss for %s", normalized_key)

        # 3. Rate limiting
        self._rate_limiter.wait()

        # 4. Acquire raw data
        try:
            raw = self._acquisition.acquire(validated_url)
        except ProfileAcquisitionError:
            # Do NOT cache failures
            logger.warning("Acquisition failed for %s", normalized_key)
            raise
        except Exception as exc:
            logger.warning("Unexpected acquisition error for %s: %s", normalized_key, type(exc).__name__)
            raise ProfileAcquisitionError(
                f"Unexpected error during acquisition: {exc}"
            ) from exc

        logger.info("Acquisition completed for %s", normalized_key)

        # 5. Normalize
        profile = normalize_profile(raw)

        # 6. Cache result (only on success)
        if self._cache is not None:
            self._cache.set(normalized_key, profile)

        return profile

    def scrape_batch(self, profile_urls: list[str]) -> list[ScrapedProfile]:
        """
        Acquire a batch of profiles, enforcing the batch size limit.

        Args:
            profile_urls: List of profile URLs.

        Returns:
            List of ScrapedProfile in the same order as input.

        Raises:
            ValueError: If the batch exceeds MAX_BATCH_SIZE.
            Any per-profile error from scrape().
        """
        validate_batch_size(profile_urls)
        return [self.scrape(url) for url in profile_urls]


# ---------------------------------------------------------------------------
# Legacy V1 API — preserved for backward compatibility
# ---------------------------------------------------------------------------

# Module-level rate limiter used by the legacy scrape_profile() function.
# The new ProfileScraper manages its own limiter per instance.
_legacy_rate_limiter = RateLimiter(delay_seconds=2.0)


def scrape_profile(
    profile_text: str,
    profile_url: str,
) -> ScrapedProfile:
    """
    Acquire profile data and convert it into a ScrapedProfile.

    LEGACY V1 API — kept for backward compatibility.
    New code should use ProfileScraper with an appropriate adapter.

    profile_text is provided directly rather than performing
    automated network acquisition.
    """
    _legacy_rate_limiter.wait()

    if not profile_text.strip():
        raise ValueError("Profile text cannot be empty")

    return parse_profile(
        profile_text,
        profile_url,
    )