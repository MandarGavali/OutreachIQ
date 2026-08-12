"""
URL validation utilities for the OutreachIQ acquisition layer.

Provides a lightweight validate_profile_url() function that rejects
obviously malformed inputs before any network call is made.

Does NOT assume any particular provider (LinkedIn, etc.) so the
acquisition layer stays provider-independent.
"""

from __future__ import annotations

from urllib.parse import urlparse


_ALLOWED_SCHEMES = {"https", "http"}
_MIN_HOST_LEN = 3  # e.g. "a.b" is the shortest plausible hostname


class InvalidProfileURLError(ValueError):
    """Raised when a profile URL fails basic validation."""


def validate_profile_url(url: str) -> str:
    """
    Validate and return the normalized profile URL.

    Args:
        url: Raw profile URL supplied by the caller.

    Returns:
        The stripped URL if it passes all checks.

    Raises:
        InvalidProfileURLError: For any structural problem with the URL.
    """
    if not url or not url.strip():
        raise InvalidProfileURLError("Profile URL must not be empty.")

    stripped = url.strip()

    try:
        parsed = urlparse(stripped)
    except Exception as exc:
        raise InvalidProfileURLError(
            f"Profile URL could not be parsed: {exc}"
        ) from exc

    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise InvalidProfileURLError(
            f"Profile URL must use http or https scheme, "
            f"got '{parsed.scheme or '(none)'}': {stripped!r}"
        )

    if not parsed.netloc or len(parsed.netloc) < _MIN_HOST_LEN:
        raise InvalidProfileURLError(
            f"Profile URL has an invalid host: {stripped!r}"
        )

    return stripped
