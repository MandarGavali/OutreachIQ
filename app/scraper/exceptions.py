"""
Scraper-specific exception hierarchy for OutreachIQ.

All acquisition errors derive from ProfileAcquisitionError so callers
can catch the whole family or individual subtypes as needed.
"""


class ProfileAcquisitionError(Exception):
    """Base class for all profile-acquisition failures."""


class ProfileNotFoundError(ProfileAcquisitionError):
    """Profile URL is valid but the profile could not be found."""


class ProfileTimeoutError(ProfileAcquisitionError):
    """Acquisition timed out before a response was received."""


class ProfileValidationError(ProfileAcquisitionError):
    """Raw profile data failed normalization / Pydantic validation."""


class ProfileAuthenticationError(ProfileAcquisitionError):
    """The acquisition source requires authentication that is unavailable."""
