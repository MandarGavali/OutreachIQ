# OutreachIQ V2 — Scraping Architecture

## Overview

The acquisition layer is the component responsible for turning a profile URL into
a canonical `ScrapedProfile` that the agent and generator consume.

It is designed to be **provider-independent**: the rest of OutreachIQ does not
care where the profile data came from.  The acquisition adapter is injected at
construction time, making every component independently testable.

---

## Data Flow

```
Profile URL
    │
    ▼
URL Validator (url_validator.py)
    │  InvalidProfileURLError on failure
    ▼
Profile Cache (cache.py)
    │  cache hit → return ScrapedProfile immediately
    │  cache miss ↓
    ▼
Rate Limiter (rate_limiter.py)
    │  randomized delay between requests
    ▼
Acquisition Adapter (adapters.py implements acquisition.py)
    │  ProfileNotFoundError / ProfileTimeoutError / ProfileAcquisitionError
    ▼
RawProfileData (acquisition.py)
    │
    ▼
Normalizer (normalizer.py)
    │  ProfileValidationError on failure
    ▼
ScrapedProfile (models/profile_models.py)
    │
    ▼
Cache population (on success only)
    │
    ▼
Agent / Generator
```

---

## Components

### `app/scraper/acquisition.py`

Defines two things:

1. **`RawProfileData`** — Pydantic model for the internal pre-normalization
   representation.  Contains fields: `profile_url`, `name`, `headline`,
   `about`, `recent_activity`, `source`, `fetched_at`.
   Does not store credentials, cookies, or tokens.

2. **`ProfileAcquisition`** — Python `Protocol` defining the contract every
   adapter must satisfy:
   ```python
   def acquire(self, profile_url: str) -> RawProfileData: ...
   ```

### `app/scraper/adapters.py`

Ships two concrete adapters:

| Adapter | Description |
|---|---|
| `FixtureProfileAdapter` | In-memory, deterministic. Used in tests and development. Register profiles by URL; supports error simulation. |
| `TextProfileAdapter` | Wraps the V1 `parser.py` pathway. Accepts pasted profile text and converts it via the existing parser. No network calls. |

A future **authorized adapter** (e.g. backed by a permitted API or an
authorized authenticated session) can be added here without touching any
other component.

### `app/scraper/normalizer.py`

`normalize_profile(raw: RawProfileData) -> ScrapedProfile`

Responsibilities:
- Strip leading/trailing whitespace
- Collapse intra-line whitespace runs
- Preserve paragraph boundaries in `about`
- Deduplicate `recent_activity` (order-preserving)
- Drop empty activity entries
- Cap activity count at 20 items
- Truncate oversized fields to schema limits
- Validate `name` is non-empty
- Return the validated `ScrapedProfile`

Does **not** invent missing information.

### `app/scraper/profile_scraper.py`

**`ProfileScraper`** — The orchestrator.  Accepts injected dependencies:

```python
ProfileScraper(
    acquisition=adapter,
    rate_limiter=RateLimiter(min_delay_seconds=1.5, max_delay_seconds=3.0),
    cache=ProfileCache(ttl_seconds=300),
)
```

Public methods:
- `scrape(profile_url) -> ScrapedProfile`
- `scrape_batch(profile_urls) -> list[ScrapedProfile]` (enforces batch limit)

The **legacy `scrape_profile(profile_text, profile_url)`** function is
preserved at module level for backward compatibility with the V1 agent tools.

### `app/scraper/rate_limiter.py`

`RateLimiter(min_delay_seconds, max_delay_seconds)`

- Randomized delay window between `min` and `max` seconds
- Uses `time.monotonic()` (wall-clock independent)
- Only sleeps the **remaining** time since the last request
- First request is not delayed if elapsed time already exceeds the target
- `delay_seconds=` kwarg preserved for backward compatibility

**Purpose**: responsible request pacing, not anti-detection evasion.

### `app/scraper/cache.py`

`ProfileCache(ttl_seconds, max_size)`

- In-memory, single-process, no external dependencies
- TTL expiry via monotonic timestamps
- FIFO eviction when `max_size` is reached
- `normalize_profile_url()` helper for stable cache keys
  - strips trailing slash
  - lowercases scheme + host (not path)
- Does **not** cache failed acquisitions
- Does **not** store credentials or session state

### `app/scraper/url_validator.py`

`validate_profile_url(url: str) -> str`

- Rejects empty/whitespace strings
- Requires `http` or `https` scheme
- Requires a plausible hostname
- Provider-agnostic (not LinkedIn-specific)
- Raises `InvalidProfileURLError` (subclass of `ValueError`)

### `app/scraper/exceptions.py`

```
ProfileAcquisitionError          ← base
├── ProfileNotFoundError         ← profile doesn't exist
├── ProfileTimeoutError          ← acquisition timed out
├── ProfileValidationError       ← normalization/Pydantic failure
└── ProfileAuthenticationError   ← auth required and unavailable
```

---

## Batch Protection

`ProfileScraper.scrape_batch()` calls `validate_batch_size()` which raises
`ValueError` if the batch exceeds `PROFILE_MAX_BATCH_SIZE` (default: 10,
configurable via `settings.PROFILE_MAX_BATCH_SIZE`).

`BatchRequest` in `app/models/request_models.py` also enforces `max_length=10`
at the API layer.

---

## Configuration

Settings in `app/config.py` (loaded from `.env`):

| Variable | Default | Description |
|---|---|---|
| `PROFILE_MIN_DELAY_SECONDS` | `1.5` | Minimum inter-request delay |
| `PROFILE_MAX_DELAY_SECONDS` | `3.0` | Maximum inter-request delay |
| `PROFILE_CACHE_TTL_SECONDS` | `300` | Cache TTL in seconds |
| `PROFILE_MAX_BATCH_SIZE` | `10` | Maximum profiles per batch |

---

## Security Design

This system does **not**:

- Bypass CAPTCHAs
- Use stealth browser fingerprinting
- Rotate proxies to evade platform detection
- Harvest credentials automatically
- Perform unauthorized LinkedIn DOM scraping at scale
- Store cookies, tokens, or session state in the profile data

The `app/auth/storage_state.json` file (Playwright authenticated session) is
listed in `.gitignore` and is never committed.

The Playwright / `browser_manager` infrastructure is preserved as a
reusable component for **authorized** browser workflows (e.g., human-assisted
sessions, approved integrations) and can be injected into a future adapter
when a permitted real-time data source is available.

---

## Test Strategy

Tests live in `tests/test_acquisition.py`.

All tests use `FixtureProfileAdapter` — no network calls, no browser,
no real LinkedIn data.

| Test | What it verifies |
|---|---|
| `test_successful_acquisition_*` | Happy path returns `ScrapedProfile` |
| `test_invalid_url_*` | Bad URLs raise `InvalidProfileURLError` |
| `test_missing_profile_*` | Unregistered URL raises `ProfileNotFoundError` |
| `test_acquisition_timeout_*` | Registered error raises `ProfileTimeoutError` |
| `test_malformed_response_*` | Empty name raises `ProfileValidationError` |
| `test_cache_hit_*` | Second call doesn't invoke the adapter |
| `test_cache_expiry_*` | After TTL, adapter is called again |
| `test_rate_limiter_wait_is_called` | Limiter `.wait()` is invoked per scrape |
| `test_batch_within_limit_*` | Batch ≤ 10 succeeds |
| `test_batch_over_limit_*` | Batch > 10 raises `ValueError` |
| `test_*_contains_no_credentials` | Exception messages carry no secrets |
| `test_end_to_end_normalized_profile` | All normalization rules verified |

Run with:
```
pytest tests/test_acquisition.py -v
pytest -v
```

---

## Provider Independence

The rest of OutreachIQ (`agent`, `generator`, `api`) consumes `ScrapedProfile`
only.  No component outside `app/scraper/` depends on:

- Which adapter is in use
- Whether a real network request was made
- Whether the data came from a fixture, pasted text, or a future API

This means swapping in a new authorized data source requires:

1. Implement a class with `acquire(self, profile_url: str) -> RawProfileData`
2. Inject it into `ProfileScraper`
3. Zero changes elsewhere

---

## Remaining Limitations (Phase 1)

- No real-time authorized external data source is connected.
  The `FixtureProfileAdapter` and `TextProfileAdapter` are the two
  production-ready adapters for this phase.
- The V1 agent (`tools.py` → `parse_profile`) still uses pasted text.
  This will be updated in Phase 2 when the custom agent loop is built.
- `ProfileCache` is in-process only.  It does not survive server restarts.
  A persistent cache (Redis, etc.) is explicitly out of scope for Phase 1.

---

## Next Step

Phase 1 acquisition layer complete; ready for **Phase 2 — Custom Agent Loop**.
