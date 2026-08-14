"""
OutreachIQ V2 — Final Demo Script

Usage
-----
  # Default (text input):
  python -m scripts.final_demo

  # Explicit source selection:
  python -m scripts.final_demo --source text
  python -m scripts.final_demo --source pdf
  python -m scripts.final_demo --source fixture

Both text and PDF use the synthetic Alex Rivera profile.
The fixture source uses DEMO_PROFILE_URL (the pre-registered adapter).

Production profile acquisition does NOT use LinkedIn DOM scraping.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from app.agent.agent_core import generate_outreach
from app.agent.tools import DEMO_PROFILE_URL
from app.models.request_models import OutreachRequest, Tone

logging.basicConfig(level=logging.INFO)
load_dotenv()

# ---------------------------------------------------------------------------
# Demo profile content (same synthetic profile for all acquisition paths)
# ---------------------------------------------------------------------------

DEMO_PROFILE_TEXT = """\
Alex Rivera
Head of Growth at TechScale — B2B SaaS | Revenue & Pipeline Strategy

About
I lead growth at TechScale, where I help B2B SaaS companies build scalable
outbound pipelines without burning out their SDR teams.
Previously scaled GTM at two Y Combinator companies from $0 to Series B.
Passionate about data-driven personalization and cutting through inbox noise.

Recent Activity
- Shared a post on why spray-and-pray cold outreach is dead in 2025
- Commented on a LinkedIn thread about AI-assisted SDR workflows
- Published an article: '5 outreach frameworks that actually get replies'
"""

DEMO_PRODUCT = (
    "OutreachIQ is an AI-powered platform that helps sales teams generate "
    "personalized, non-spammy outreach messages grounded in real profile data."
)

DEMO_PDF_PATH = Path(__file__).parent.parent / "examples" / "sample_profile.pdf"


# ---------------------------------------------------------------------------
# Source dispatch
# ---------------------------------------------------------------------------

def _run_text_demo() -> None:
    print("\n[Profile Source] Text (user-pasted)\n")
    print("Profile Text Provided")
    print("---------------------")
    print(DEMO_PROFILE_TEXT)
    print()

    request = OutreachRequest(
        profile_text=DEMO_PROFILE_TEXT,
        product_description=DEMO_PRODUCT,
        tone=Tone.CASUAL,
    )
    print("Starting agent loop (text acquisition — no rate limiting, no cache)...")
    result = generate_outreach(request)
    _print_result(result, source_label="Text")


def _run_pdf_demo(pdf_paths_str: list[str]) -> None:
    print("\n[Profile Source] PDF Upload\n")

    pdf_paths = [Path(p) for p in pdf_paths_str]
    for p in pdf_paths:
        if not p.exists() or not p.is_file():
            print(f"PDF file not found: {p}")
            sys.exit(1)

    print(f"Processing {len(pdf_paths)} PDF(s)...")
    print()

    # Extract profile via PDFProfileAdapter, then pass to agent
    from app.scraper.pdf_adapter import PDFProfileAdapter
    from app.scraper.normalizer import normalize_profile
    from app.scraper.exceptions import ProfileAcquisitionError

    adapter = PDFProfileAdapter()
    
    successful = 0
    failed = 0
    
    for pdf_path in pdf_paths:
        print(f"--- Processing {pdf_path.name} ---")
        try:
            raw = adapter.acquire_from_pdf(str(pdf_path))
        except ProfileAcquisitionError as e:
            print(f"Acquisition Error: {e}\n")
            failed += 1
            continue
            
        except Exception as e:
            print(f"Unexpected Error: {e}\n")
            failed += 1
            continue

        profile = normalize_profile(raw)

        print("Extracted Profile")
        print("-----------------")
        print(f"Name: {profile.name}")
        print(f"Headline: {profile.headline}")
        print(f"About: {profile.about[:100] if profile.about else ''}...")
        print(f"Activity ({len(profile.recent_activity)} items)")
        print()

        # Build a text request from the extracted profile fields
        request = OutreachRequest(
            profile_text=(
                f"Name: {profile.name}\n"
                f"Headline: {profile.headline}\n\n"
                f"About\n{profile.about}\n\n"
                f"Recent Activity\n"
                + "\n".join(f"- {a}" for a in profile.recent_activity)
            ),
            product_description=DEMO_PRODUCT,
            tone=Tone.CASUAL,
        )

        print(f"Starting agent loop for {profile.name} (PDF acquisition -> text -> agent)...")
        result = generate_outreach(request, pre_scraped_profile=profile)
        _print_result(result, source_label=f"PDF ({pdf_path.name})")
        successful += 1

    print("=" * 44)
    print("       BATCH PDF SUMMARY")
    print("=" * 44)
    print(f"Total:      {len(pdf_paths)}")
    print(f"Successful: {successful}")
    print(f"Failed:     {failed}")
    print("=" * 44)



def _run_fixture_demo() -> None:
    print("\n[Profile Source] Fixture (pre-registered)\n")
    print(f"Profile URL: {DEMO_PROFILE_URL}")
    print()

    request = OutreachRequest(
        profile_url=DEMO_PROFILE_URL,
        product_description=DEMO_PRODUCT,
        tone=Tone.CASUAL,
    )
    print("Starting agent loop (fixture acquisition)...")
    result = generate_outreach(request)
    _print_result(result, source_label="Fixture")


def _print_result(result, source_label: str) -> None:
    print()
    print("=" * 44)
    print("       OUTREACHIQ V2 DEMO")
    print("=" * 44)
    print()
    print(f"Source: {source_label}")
    print(f"Product: {DEMO_PRODUCT[:60]}...")
    print(f"Tone: casual")
    print()
    print("=" * 44)
    print("       FINAL RESULT SUMMARY")
    print("=" * 44)
    print()
    print("Final Message")
    print("-------------")
    print(f"To: {result.recipient_name}")
    print()
    print(result.message)
    print()
    print("Reason for Outreach")
    print("-------------------")
    print(result.reason_for_outreach)
    print()
    print("=" * 44)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="OutreachIQ V2 Final Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m scripts.final_demo                  # default (text)
  python -m scripts.final_demo --source text    # user-pasted text
  python -m scripts.final_demo --source pdf --pdf "PATH_TO_REAL_PROFILE_PDF" # PDF upload
  python -m scripts.final_demo --source fixture # pre-registered fixture
        """,
    )
    parser.add_argument(
        "--source",
        choices=["text", "pdf", "fixture"],
        default="text",
        help="Profile acquisition source (default: text)",
    )
    parser.add_argument(
        "--pdf",
        type=str,
        nargs="+",
        help="Path(s) to the PDF file(s) (required if --source pdf)",
    )
    args = parser.parse_args()

    if args.source == "pdf" and not args.pdf:
        print("PDF source requires --pdf PATH")
        sys.exit(1)

    print("=" * 44)
    print("  OUTREACHIQ V2 — PRODUCTION DEMO")
    print("=" * 44)
    print("Production profile acquisition does NOT use LinkedIn DOM scraping.")
    print()

    if args.source == "text":
        _run_text_demo()
    elif args.source == "pdf":
        _run_pdf_demo(args.pdf)
    elif args.source == "fixture":
        _run_fixture_demo()


if __name__ == "__main__":
    main()
