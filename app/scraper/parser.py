"""
Profile text parser for OutreachIQ.

parse_profile_text()
--------------------
The single shared parser for all text-based profile inputs.

Used by:
    - TextProfileAdapter
    - PDFProfileAdapter

Pipeline:

    raw text
        ↓
    parse_profile_text()
        ↓
    RawProfileData
        ↓
    normalize_profile()
        ↓
    ScrapedProfile


Design principles
-----------------
- Accepts manually pasted profile text.
- Accepts LinkedIn "Save to PDF" extracted text.
- Does NOT access LinkedIn.
- Does NOT make network requests.
- Does NOT invent missing profile information.
- Returns RawProfileData, not ScrapedProfile.
- Handles missing optional sections.
- Handles sidebar metadata appearing before the real profile header.
- Preserves the legacy parse_profile() compatibility shim.
"""

from __future__ import annotations

import re
from typing import Optional

from app.scraper.acquisition import RawProfileData


# ---------------------------------------------------------------------------
# Section header recognition
# ---------------------------------------------------------------------------

_ABOUT_HEADERS: frozenset[str] = frozenset(
    {
        "about",
        "about:",
        "summary",
        "summary:",
        "bio",
        "bio:",
        "background",
        "background:",
    }
)

_ACTIVITY_HEADERS: frozenset[str] = frozenset(
    {
        "recent activity",
        "recent activity:",
        "activity",
        "activity:",
        "posts",
        "posts:",
        "recent posts",
        "recent posts:",
    }
)

_HEADLINE_HEADERS: frozenset[str] = frozenset(
    {
        "headline",
        "headline:",
        "title",
        "title:",
        "position",
        "position:",
        "role",
        "role:",
    }
)

# Sections that commonly appear in LinkedIn PDF sidebars.
# These should never become someone's name/headline.
_SIDEBAR_HEADERS: frozenset[str] = frozenset(
    {
        "contact",
        "contact:",
        "top skills",
        "top skills:",
        "skills",
        "skills:",
        "certifications",
        "certifications:",
        "languages",
        "languages:",
        "honors & awards",
        "honors & awards:",
        "publications",
        "publications:",
        "projects",
        "projects:",
        "organizations",
        "organizations:",
        "interests",
        "interests:",
        "volunteering",
        "volunteering:",
        "courses",
        "courses:",
        "test scores",
        "test scores:",
        "patents",
        "patents:",
    }
)

# Sections which usually mark the beginning of the main profile content.
_MAIN_CONTENT_HEADERS: frozenset[str] = frozenset(
    {
        "summary",
        "summary:",
        "about",
        "about:",
        "experience",
        "experience:",
        "education",
        "education:",
        "licenses & certifications",
        "licenses & certifications:",
    }
)

_ALL_HEADERS: frozenset[str] = (
    _ABOUT_HEADERS
    | _ACTIVITY_HEADERS
    | _HEADLINE_HEADERS
    | _SIDEBAR_HEADERS
    | _MAIN_CONTENT_HEADERS
)


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------

def _normalize_whitespace(text: str) -> str:
    """
    Normalize horizontal whitespace while preserving line boundaries.
    """
    lines = [
        re.sub(r"[^\S\n]+", " ", line).strip()
        for line in text.splitlines()
    ]

    result_lines: list[str] = []
    blank_count = 0

    for line in lines:
        if not line:
            blank_count += 1

            if blank_count <= 2:
                result_lines.append(line)
        else:
            blank_count = 0
            result_lines.append(line)

    return "\n".join(result_lines).strip()


def _clean_lines(text: str) -> list[str]:
    """
    Return normalized non-empty lines.
    """
    normalized = _normalize_whitespace(text)

    return [
        line.strip()
        for line in normalized.splitlines()
        if line.strip()
    ]


def _is_section_header(line: str) -> bool:
    """
    Return True when the line is a recognized section header.
    """
    return line.strip().lower() in _ALL_HEADERS


def _is_sidebar_header(line: str) -> bool:
    """
    Return True when the line represents LinkedIn sidebar metadata.
    """
    return line.strip().lower() in _SIDEBAR_HEADERS


def _is_main_content_header(line: str) -> bool:
    """
    Return True when the line starts a major profile section.
    """
    return line.strip().lower() in _MAIN_CONTENT_HEADERS


def _is_url(line: str) -> bool:
    """
    Detect URLs and LinkedIn URL-like lines.
    """
    value = line.strip().lower()

    return (
        value.startswith("http://")
        or value.startswith("https://")
        or value.startswith("www.")
        or "linkedin.com/" in value
    )


def _is_parenthetical_metadata(line: str) -> bool:
    """
    Detect PDF metadata such as:

        (LinkedIn)
        (Company)
    """
    value = line.strip()

    return (
        len(value) >= 2
        and value.startswith("(")
        and value.endswith(")")
    )


def _is_bullet(line: str) -> bool:
    """
    Detect common bullet prefixes.
    """
    return bool(re.match(r"^[-•*·▸►▪◦]\s*", line))


# ---------------------------------------------------------------------------
# Name detection
# ---------------------------------------------------------------------------

_NAME_STOPWORDS: frozenset[str] = frozenset(
    {
        "contact",
        "summary",
        "about",
        "experience",
        "education",
        "skills",
        "top",
        "certifications",
        "languages",
        "projects",
        "publications",
        "organizations",
        "interests",
        "profile",
        "linkedin",
        "introduction",
        "certificate",
        "certification",
        "company",
        "location",
    }
)


def _looks_like_person_name(line: str) -> bool:
    """
    Heuristic for identifying a person's name.

    This intentionally uses several weak signals rather than relying on
    a single hard-coded name.

    Examples accepted:

        ARYAN RAJ
        Aryan Raj
        John Doe
        Sarah Connor
        O'Connor Smith

    Examples rejected:

        Contact
        Top Skills
        www.linkedin.com/in/example
        Introduction to FOCUS
        Certificate of completion: Claude 101
    """
    value = line.strip()

    if not value:
        return False

    if _is_url(value):
        return False

    if _is_section_header(value):
        return False

    if _is_parenthetical_metadata(value):
        return False

    if ":" in value:
        return False

    if any(char.isdigit() for char in value):
        return False

    words = value.split()

    # Most names are 2-4 words. Allow 1-word names only for explicit
    # name-field parsing elsewhere.
    if not 2 <= len(words) <= 4:
        return False

    lowered_words = {word.lower().strip(".,") for word in words}

    if lowered_words & _NAME_STOPWORDS:
        return False

    # Reject lines containing obvious sentence punctuation.
    if any(char in value for char in ".!?;|/\\"):
        return False

    # Name characters: letters, spaces, apostrophes and hyphens.
    if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ'’\- ]+", value):
        return False

    return True


# ---------------------------------------------------------------------------
# Headline detection
# ---------------------------------------------------------------------------

def _looks_like_headline(line: str) -> bool:
    """
    Determine whether a line plausibly represents a professional headline.

    We intentionally keep this permissive because LinkedIn headlines can
    contain many formats:

        Founder @ Planck Labs
        Software Engineer | AI/ML
        Building products for developers
        Master AI before it masters you | Founder @ Planck Labs
    """
    value = line.strip()

    if not value:
        return False

    if _is_url(value):
        return False

    if _is_section_header(value):
        return False

    if _is_parenthetical_metadata(value):
        return False

    if _is_bullet(value):
        return False

    if len(value) < 3:
        return False

    # Avoid treating long paragraph-like text as the headline.
    if len(value) > 250:
        return False

    return True


# ---------------------------------------------------------------------------
# LinkedIn PDF header detection
# ---------------------------------------------------------------------------

def _find_pdf_profile_header(
    lines: list[str],
) -> tuple[Optional[str], Optional[str], Optional[int]]:
    """
    Locate the actual LinkedIn profile header.

    LinkedIn PDF exports can place sidebar information before the main
    profile identity, for example:

        Contact
        www.linkedin.com/in/example
        (LinkedIn)
        Top Skills
        ...
        Certifications
        ...
        ARYAN RAJ
        Master AI before it masters you | Founder @ Planck Labs
        Bengaluru, Karnataka, India
        Summary

    The old parser incorrectly interpreted "Contact" as the name.

    This function searches for a plausible name/headline pair and gives
    preference to candidates that appear immediately before a major
    profile section such as Summary or Experience.
    """
    candidates: list[tuple[int, int, int]] = []

    for index in range(len(lines) - 1):
        name_candidate = lines[index]
        headline_candidate = lines[index + 1]

        if not _looks_like_person_name(name_candidate):
            continue

        if not _looks_like_headline(headline_candidate):
            continue

        score = 0

        # Strong signal: candidate is followed by a likely location.
        if index + 2 < len(lines):
            next_line = lines[index + 2]

            if (
                not _is_section_header(next_line)
                and not _is_url(next_line)
                and len(next_line) < 150
            ):
                score += 2

        # Strong signal: candidate is followed shortly by Summary/About.
        for lookahead in range(2, 5):
            position = index + lookahead

            if position >= len(lines):
                break

            if lines[position].lower() in _MAIN_CONTENT_HEADERS:
                score += 5
                break

        # Main content candidates are preferred over early sidebar noise.
        score += min(index, 10)

        candidates.append((score, index, index + 1))

    if not candidates:
        return None, None, None

    # Highest score wins.
    _, name_index, headline_index = max(
        candidates,
        key=lambda candidate: candidate[0],
    )

    return (
        lines[name_index],
        lines[headline_index],
        name_index,
    )


# ---------------------------------------------------------------------------
# Explicit field extraction
# ---------------------------------------------------------------------------

def _extract_inline_fields(
    lines: list[str],
) -> tuple[Optional[str], Optional[str]]:
    """
    Extract explicit fields such as:

        Name: John Doe
        Headline: Senior Engineer
    """
    name: Optional[str] = None
    headline: Optional[str] = None

    for line in lines:
        match = re.match(
            r"^(name)\s*:\s*(.+)$",
            line,
            re.IGNORECASE,
        )

        if match and not name:
            name = match.group(2).strip()
            continue

        match = re.match(
            r"^(headline|title|position|role)\s*:\s*(.+)$",
            line,
            re.IGNORECASE,
        )

        if match and not headline:
            headline = match.group(2).strip()

    return name, headline


# ---------------------------------------------------------------------------
# About / activity extraction
# ---------------------------------------------------------------------------

def _extract_sections(
    lines: list[str],
) -> tuple[list[str], list[str]]:
    """
    Extract About/Summary and Recent Activity sections.

    Returns:
        about_lines, activity_lines
    """
    about_lines: list[str] = []
    activity_lines: list[str] = []

    state: Optional[str] = None

    for line in lines:
        lower = line.lower()

        if lower in _ABOUT_HEADERS:
            state = "about"
            continue

        if lower in _ACTIVITY_HEADERS:
            state = "activity"
            continue

        # A new major section terminates About/Activity extraction.
        if state and _is_main_content_header(line):
            if lower not in _ABOUT_HEADERS and lower not in _ACTIVITY_HEADERS:
                state = None
                continue

        # Sidebar sections should terminate the current extraction state.
        if state and _is_sidebar_header(line):
            state = None
            continue

        if state == "about":
            about_lines.append(line)

        elif state == "activity":
            cleaned = re.sub(
                r"^[-•*·▸►▪◦]\s*",
                "",
                line,
            )

            if cleaned:
                activity_lines.append(cleaned)

    return about_lines, activity_lines


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_profile_text(
    text: str,
    profile_url: Optional[str] = None,
    source: str = "text",
) -> RawProfileData:
    """
    Parse free-form profile text into RawProfileData.

    Args:
        text:
            Raw profile text from either:
                - manually pasted input
                - LinkedIn Save-to-PDF extraction

        profile_url:
            Optional profile URL supplied by the application.

        source:
            Acquisition source such as "text", "pdf", or "fixture".

    Returns:
        RawProfileData ready for normalize_profile().

    Raises:
        ValueError:
            If the input is empty or no usable name can be found.
    """
    if not text or not text.strip():
        raise ValueError("Profile text is empty.")

    lines = _clean_lines(text)

    if not lines:
        raise ValueError("Profile text contains no usable content.")

    # -----------------------------------------------------------------------
    # 1. Explicit fields have highest priority.
    # -----------------------------------------------------------------------

    explicit_name, explicit_headline = _extract_inline_fields(lines)

    name = explicit_name or ""
    headline = explicit_headline or ""

    # -----------------------------------------------------------------------
    # 2. Detect LinkedIn PDF-style profile header.
    #
    # This is the important fix for the real-world PDF test.
    # -----------------------------------------------------------------------

    pdf_name, pdf_headline, pdf_name_index = _find_pdf_profile_header(lines)

    if not name and pdf_name:
        name = pdf_name

    if not headline and pdf_headline:
        headline = pdf_headline

    # -----------------------------------------------------------------------
    # 3. Fallback to simple pasted-text format.
    #
    # Example:
    #
    # John Doe
    # Senior Software Engineer
    #
    # About
    # ...
    # -----------------------------------------------------------------------

    if not name:
        for index, line in enumerate(lines):
            if _is_section_header(line):
                continue

            if _is_url(line):
                continue

            if _is_parenthetical_metadata(line):
                continue

            # Only accept a line as a name if it actually looks like
        # a person's name. Do not blindly accept arbitrary text.

            if not _looks_like_person_name(line):
                continue

            name = line

            if not headline and index + 1 < len(lines):
                next_line = lines[index + 1]

                if _looks_like_headline(next_line):
                    headline = next_line

            break

    # -----------------------------------------------------------------------
    # 4. Validate name.
    # -----------------------------------------------------------------------

    if not name:
        raise ValueError(
            "Profile text must contain a recognizable profile name."
        )

    # -----------------------------------------------------------------------
    # 5. Extract About/Summary and Recent Activity.
    # -----------------------------------------------------------------------

    about_lines, activity_lines = _extract_sections(lines)

    about = "\n".join(about_lines).strip()

    # -----------------------------------------------------------------------
    # 6. Optional LinkedIn URL detection.
    #
    # Only extracts metadata. It NEVER performs a network request.
    # -----------------------------------------------------------------------

    extracted_url = profile_url

    if not extracted_url:
        for line in lines:
            if "linkedin.com/in/" in line.lower():
                url_match = re.search(
                    r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9\-_%]+",
                    line,
                    re.IGNORECASE,
                )

                if url_match:
                    extracted_url = url_match.group(0)
                    break

    return RawProfileData(
        profile_url=extracted_url,
        name=name.strip(),
        headline=headline.strip(),
        about=about,
        recent_activity=activity_lines,
        source=source,
    )


# ---------------------------------------------------------------------------
# Backward-compatibility shim
# ---------------------------------------------------------------------------

def parse_profile(
    profile_text: str,
    profile_url: str,
) -> "ScrapedProfile":  # type: ignore[name-defined]
    """
    Legacy V1 compatibility shim.

    Converts raw profile text into a ScrapedProfile.

    New code should use:

        parse_profile_text()
            ↓
        RawProfileData
            ↓
        normalize_profile()
    """
    from app.models.profile_models import ScrapedProfile
    from app.scraper.normalizer import normalize_profile

    raw = parse_profile_text(
        profile_text,
        profile_url=profile_url,
        source="text_legacy",
    )

    return normalize_profile(raw)