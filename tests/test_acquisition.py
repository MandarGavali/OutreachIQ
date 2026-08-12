"""
Integration tests for the Phase 1.9 acquisition pipeline.

Tests the full flow:
  FixtureProfileAdapter → ProfileScraper → normalize_profile → ScrapedProfile

These tests use NO network connections, NO real LinkedIn data,
and NO browser automation.  All acquisition is driven by the
FixtureProfileAdapter with pre-registered data or error stubs.

Test coverage:
  1.  Successful acquisition returns ScrapedProfile
  2.  Invalid URL raises InvalidProfileURLError
  3.  Missing profile raises ProfileNotFoundError
  4.  Acquisition timeout raises ProfileTimeoutError
  5.  Malformed provider response raises ProfileValidationError
  6.  Cache hit avoids second adapter call
  7.  Cache expiry causes second adapter call
  8.  Rate limiter is applied (mock sleep)
  9.  Batch within limit succeeds
  10. Batch over limit raises ValueError
  11. No credentials leak in exception messages or logs
  12. End-to-end normalized profile — all fields verified
"""

from __future__ import annotations

import time
import logging
from unittest.mock import MagicMock, patch

import pytest

from app.models.profile_models import ScrapedProfile
from app.scraper.acquisition import RawProfileData
from app.scraper.adapters import FixtureProfileAdapter
from app.scraper.cache import ProfileCache
from app.scraper.exceptions import (
    ProfileAcquisitionError,
    ProfileNotFoundError,
    ProfileTimeoutError,
    ProfileValidationError,
)
from app.scraper.normalizer import normalize_profile
from app.scraper.profile_scraper import (
    MAX_BATCH_SIZE,
    ProfileScraper,
    validate_batch_size,
)
from app.scraper.rate_limiter import RateLimiter
from app.scraper.url_validator import InvalidProfileURLError, validate_profile_url


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_raw(
    profile_url: str = "https://linkedin.com/in/test-user",
    name: str = "Test User",
    headline: str = "Software Engineer",
    about: str = "I build things.",
    recent_activity: list[str] | None = None,
    source: str = "fixture",
) -> RawProfileData:
    return RawProfileData(
        profile_url=profile_url,
        name=name,
        headline=headline,
        about=about,
        recent_activity=recent_activity or [],
        source=source,
    )


def _make_scraper(
    adapter: FixtureProfileAdapter,
    ttl_seconds: float = 60.0,
    min_delay: float = 0.0,
    max_delay: float = 0.0,
) -> tuple[ProfileScraper, ProfileCache]:
    """Return a ProfileScraper with a fresh cache and zero-delay rate limiter."""
    cache = ProfileCache(ttl_seconds=ttl_seconds)
    scraper = ProfileScraper(
        acquisition=adapter,
        rate_limiter=RateLimiter(
            min_delay_seconds=min_delay,
            max_delay_seconds=max_delay,
        ),
        cache=cache,
    )
    return scraper, cache


# ===========================================================================
# Test 1 — Successful acquisition
# ===========================================================================

def test_successful_acquisition_returns_scraped_profile():
    url = "https://linkedin.com/in/jane-doe"
    adapter = FixtureProfileAdapter()
    adapter.register(url, _make_raw(profile_url=url, name="Jane Doe"))
    scraper, _ = _make_scraper(adapter)

    profile = scraper.scrape(url)

    assert isinstance(profile, ScrapedProfile)
    assert profile.name == "Jane Doe"


# ===========================================================================
# Test 2 — Invalid URL
# ===========================================================================

@pytest.mark.parametrize("bad_url", [
    "",
    "   ",
    "not-a-url",
    "ftp://linkedin.com/in/jane",
    "mailto:jane@example.com",
    "https://",
    "http://",
])
def test_invalid_url_raises_invalid_profile_url_error(bad_url):
    with pytest.raises(InvalidProfileURLError):
        validate_profile_url(bad_url)


def test_scraper_rejects_invalid_url():
    adapter = FixtureProfileAdapter()
    scraper, _ = _make_scraper(adapter)

    with pytest.raises(InvalidProfileURLError):
        scraper.scrape("not-a-url")


# ===========================================================================
# Test 3 — Missing profile
# ===========================================================================

def test_missing_profile_raises_not_found():
    url = "https://linkedin.com/in/nobody"
    adapter = FixtureProfileAdapter()
    # No fixture registered for this URL
    scraper, _ = _make_scraper(adapter)

    with pytest.raises(ProfileNotFoundError):
        scraper.scrape(url)


# ===========================================================================
# Test 4 — Acquisition timeout
# ===========================================================================

def test_acquisition_timeout_raises_timeout_error():
    url = "https://linkedin.com/in/slow-user"
    adapter = FixtureProfileAdapter()
    adapter.register_error(url, ProfileTimeoutError("Timed out after 30s"))
    scraper, _ = _make_scraper(adapter)

    with pytest.raises(ProfileTimeoutError):
        scraper.scrape(url)


# ===========================================================================
# Test 5 — Malformed provider response
# ===========================================================================

def test_malformed_response_raises_validation_error():
    url = "https://linkedin.com/in/bad-data"
    adapter = FixtureProfileAdapter()
    # Register a fixture with an empty name — normalizer should reject it
    adapter.register(url, _make_raw(profile_url=url, name="   "))
    scraper, _ = _make_scraper(adapter)

    with pytest.raises(ProfileValidationError):
        scraper.scrape(url)


# ===========================================================================
# Test 6 — Cache hit avoids second adapter call
# ===========================================================================

def test_cache_hit_skips_adapter():
    url = "https://linkedin.com/in/cached-user"
    adapter = FixtureProfileAdapter()
    adapter.register(url, _make_raw(profile_url=url, name="Cached User"))
    scraper, cache = _make_scraper(adapter, ttl_seconds=60.0)

    # Wrap acquire to count calls
    original_acquire = adapter.acquire
    call_count = 0

    def counting_acquire(u):
        nonlocal call_count
        call_count += 1
        return original_acquire(u)

    adapter.acquire = counting_acquire

    scraper.scrape(url)   # first call — hits adapter
    scraper.scrape(url)   # second call — should hit cache

    assert call_count == 1, "Adapter should have been called only once"


# ===========================================================================
# Test 7 — Cache expiry causes re-acquisition
# ===========================================================================

def test_cache_expiry_causes_readquisition():
    url = "https://linkedin.com/in/expiry-user"
    adapter = FixtureProfileAdapter()
    adapter.register(url, _make_raw(profile_url=url, name="Expiry User"))

    # Very short TTL
    cache = ProfileCache(ttl_seconds=0.05)
    scraper = ProfileScraper(
        acquisition=adapter,
        rate_limiter=RateLimiter(min_delay_seconds=0.0, max_delay_seconds=0.0),
        cache=cache,
    )

    original_acquire = adapter.acquire
    call_count = 0

    def counting_acquire(u):
        nonlocal call_count
        call_count += 1
        return original_acquire(u)

    adapter.acquire = counting_acquire

    scraper.scrape(url)
    time.sleep(0.1)        # Let TTL expire
    scraper.scrape(url)

    assert call_count == 2, "Adapter should be called again after TTL expires"


# ===========================================================================
# Test 8 — Rate limiter is applied (mock sleep, no real waiting)
# ===========================================================================

def test_rate_limiter_wait_is_called():
    url = "https://linkedin.com/in/rate-limited"
    adapter = FixtureProfileAdapter()
    adapter.register(url, _make_raw(profile_url=url, name="Rate Limited"))

    mock_limiter = MagicMock()
    scraper = ProfileScraper(
        acquisition=adapter,
        rate_limiter=mock_limiter,
        cache=None,
    )

    scraper.scrape(url)

    mock_limiter.wait.assert_called_once()


# ===========================================================================
# Test 9 — Batch within limit
# ===========================================================================

def test_batch_within_limit_succeeds():
    adapter = FixtureProfileAdapter()
    urls = []
    for i in range(MAX_BATCH_SIZE):
        url = f"https://linkedin.com/in/user-{i}"
        adapter.register(url, _make_raw(profile_url=url, name=f"User {i}"))
        urls.append(url)

    scraper, _ = _make_scraper(adapter)
    profiles = scraper.scrape_batch(urls)

    assert len(profiles) == MAX_BATCH_SIZE
    for p in profiles:
        assert isinstance(p, ScrapedProfile)


# ===========================================================================
# Test 10 — Batch over limit
# ===========================================================================

def test_batch_over_limit_raises():
    urls = [f"https://linkedin.com/in/user-{i}" for i in range(MAX_BATCH_SIZE + 1)]

    with pytest.raises(ValueError, match=str(MAX_BATCH_SIZE)):
        validate_batch_size(urls)


# ===========================================================================
# Test 11 — No credentials leakage in exceptions
# ===========================================================================

SENSITIVE_PATTERNS = [
    "password",
    "cookie",
    "storage_state",
    "api_key",
    "GOOGLE_API_KEY",
    "token",
    "secret",
]


def test_not_found_error_contains_no_credentials():
    url = "https://linkedin.com/in/ghost"
    adapter = FixtureProfileAdapter()
    # Not registered — will raise ProfileNotFoundError
    try:
        adapter.acquire(url)
    except ProfileNotFoundError as exc:
        message = str(exc).lower()
        for pattern in SENSITIVE_PATTERNS:
            assert pattern.lower() not in message, (
                f"Sensitive pattern '{pattern}' found in exception message"
            )


def test_timeout_error_contains_no_credentials():
    url = "https://linkedin.com/in/slow"
    adapter = FixtureProfileAdapter()
    adapter.register_error(
        url,
        ProfileTimeoutError("Timed out — no auth details here"),
    )
    try:
        adapter.acquire(url)
    except ProfileTimeoutError as exc:
        message = str(exc).lower()
        for pattern in SENSITIVE_PATTERNS:
            assert pattern.lower() not in message, (
                f"Sensitive pattern '{pattern}' found in exception message"
            )


# ===========================================================================
# Test 12 — End-to-end normalized profile
# ===========================================================================

def test_end_to_end_normalized_profile():
    url = "https://linkedin.com/in/full-profile"
    raw = RawProfileData(
        profile_url=url,
        name="  Jane Doe  ",                # should be stripped
        headline="  ML Engineer  ",          # should be stripped
        about="  Building AI systems.\n\nPassionate about research.  ",
        recent_activity=[
            "  Published a paper on LLMs  ",   # stripped
            "Shared a post about MLOps",
            "",                                 # should be dropped
            "Shared a post about MLOps",        # duplicate — should be dropped
        ],
        source="fixture",
    )

    adapter = FixtureProfileAdapter()
    adapter.register(url, raw)
    scraper, _ = _make_scraper(adapter)

    profile = scraper.scrape(url)

    assert profile.name == "Jane Doe"
    assert profile.headline == "ML Engineer"
    assert "Building AI systems." in profile.about
    assert "Passionate about research." in profile.about
    # Empty entry and duplicate removed → 2 unique non-empty activities
    assert len(profile.recent_activity) == 2
    assert profile.recent_activity[0] == "Published a paper on LLMs"
    assert profile.recent_activity[1] == "Shared a post about MLOps"
    assert str(profile.profile_url) in (url, url + "/")


# ===========================================================================
# Normalizer unit tests
# ===========================================================================

def test_normalize_profile_strips_whitespace():
    raw = _make_raw(name="  Alice  ", headline="  Engineer  ", about="  Works here.  ")
    profile = normalize_profile(raw)
    assert profile.name == "Alice"
    assert profile.headline == "Engineer"
    assert profile.about == "Works here."


def test_normalize_profile_requires_name():
    raw = _make_raw(name="")
    with pytest.raises(ProfileValidationError, match="name"):
        normalize_profile(raw)


def test_normalize_profile_deduplicates_activities():
    raw = _make_raw(
        recent_activity=["Post A", "Post B", "Post A", "Post C"]
    )
    profile = normalize_profile(raw)
    assert profile.recent_activity == ["Post A", "Post B", "Post C"]


def test_normalize_profile_drops_empty_activities():
    raw = _make_raw(recent_activity=["Post A", "", "   ", "Post B"])
    profile = normalize_profile(raw)
    assert "" not in profile.recent_activity
    assert "   " not in profile.recent_activity
    assert len(profile.recent_activity) == 2


def test_normalize_profile_caps_activity_count():
    raw = _make_raw(recent_activity=[f"Post {i}" for i in range(50)])
    profile = normalize_profile(raw)
    assert len(profile.recent_activity) <= 20


def test_normalize_profile_truncates_long_name():
    raw = _make_raw(name="A" * 200)
    profile = normalize_profile(raw)
    assert len(profile.name) == 100


# ===========================================================================
# Rate limiter unit tests
# ===========================================================================

def test_rate_limiter_respects_min_max():
    limiter = RateLimiter(min_delay_seconds=0.05, max_delay_seconds=0.10)
    start = time.monotonic()
    limiter.wait()  # First call — no prior request, waits target - elapsed
    limiter.wait()  # Second call — will sleep because elapsed < target
    elapsed = time.monotonic() - start
    # At minimum one delay should have fired (~0.05 s minimum)
    assert elapsed >= 0.04  # generous lower bound


def test_rate_limiter_rejects_negative_min():
    with pytest.raises(ValueError, match="negative"):
        RateLimiter(min_delay_seconds=-1.0, max_delay_seconds=1.0)


def test_rate_limiter_rejects_max_less_than_min():
    with pytest.raises(ValueError, match="max_delay_seconds"):
        RateLimiter(min_delay_seconds=2.0, max_delay_seconds=1.0)


def test_rate_limiter_zero_delay_does_not_sleep():
    """A zero-delay limiter must not block execution."""
    limiter = RateLimiter(min_delay_seconds=0.0, max_delay_seconds=0.0)
    start = time.monotonic()
    for _ in range(5):
        limiter.wait()
    elapsed = time.monotonic() - start
    assert elapsed < 0.5  # should complete nearly instantly


def test_rate_limiter_legacy_delay_seconds_kwarg():
    """Backward-compat: old delay_seconds= kwarg still works."""
    limiter = RateLimiter(delay_seconds=1.0)
    assert limiter.min_delay_seconds == 1.0
    assert limiter.max_delay_seconds == 1.0


# ===========================================================================
# Cache unit tests
# ===========================================================================

def test_cache_hit_returns_profile():
    cache = ProfileCache(ttl_seconds=60)
    url = "https://linkedin.com/in/cache-test"
    profile = ScrapedProfile(
        profile_url=url, name="Cache Test", headline="Engineer"
    )
    cache.set(url, profile)
    result = cache.get(url)
    assert result is not None
    assert result.name == "Cache Test"


def test_cache_miss_returns_none():
    cache = ProfileCache(ttl_seconds=60)
    result = cache.get("https://linkedin.com/in/nobody")
    assert result is None


def test_cache_expiry():
    cache = ProfileCache(ttl_seconds=0.05)
    url = "https://linkedin.com/in/expiry"
    profile = ScrapedProfile(profile_url=url, name="Expiry")
    cache.set(url, profile)
    time.sleep(0.1)
    assert cache.get(url) is None


def test_cache_invalidate():
    cache = ProfileCache(ttl_seconds=60)
    url = "https://linkedin.com/in/invalidate"
    profile = ScrapedProfile(profile_url=url, name="Invalidate")
    cache.set(url, profile)
    cache.invalidate(url)
    assert cache.get(url) is None


def test_cache_max_size_eviction():
    cache = ProfileCache(ttl_seconds=60, max_size=3)
    for i in range(4):
        url = f"https://linkedin.com/in/user-{i}"
        profile = ScrapedProfile(profile_url=url, name=f"User {i}")
        cache.set(url, profile)
    # Should have evicted the oldest entry to stay at max_size
    assert len(cache) <= 3


def test_cache_normalizes_trailing_slash():
    cache = ProfileCache(ttl_seconds=60)
    url_with_slash = "https://linkedin.com/in/jane/"
    url_without_slash = "https://linkedin.com/in/jane"
    profile = ScrapedProfile(profile_url=url_without_slash, name="Jane")
    cache.set(url_with_slash, profile)
    result = cache.get(url_without_slash)
    assert result is not None


# ===========================================================================
# URL validator unit tests
# ===========================================================================

def test_valid_https_url():
    result = validate_profile_url("https://linkedin.com/in/jane-doe")
    assert result == "https://linkedin.com/in/jane-doe"


def test_valid_http_url():
    result = validate_profile_url("http://example.com/profile/123")
    assert result == "http://example.com/profile/123"


def test_empty_url_raises():
    with pytest.raises(InvalidProfileURLError):
        validate_profile_url("")


def test_whitespace_url_raises():
    with pytest.raises(InvalidProfileURLError):
        validate_profile_url("   ")


def test_ftp_url_raises():
    with pytest.raises(InvalidProfileURLError):
        validate_profile_url("ftp://linkedin.com/in/jane")


def test_no_scheme_url_raises():
    with pytest.raises(InvalidProfileURLError):
        validate_profile_url("linkedin.com/in/jane")
