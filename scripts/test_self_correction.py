"""
Manual demo of the Phase 3 Self-Correction loop.

Run:
    python -m scripts.test_self_correction

This script demonstrates the generate → evaluate → regenerate loop using
real Gemini calls (requires GOOGLE_API_KEY in .env).

It supplies a strong profile but a weak initial message to force the
evaluator to reject the first attempt and trigger regeneration.

Do NOT include this in pytest — it requires a real API key.
"""

import logging
from pprint import pprint

from app.agent.evaluator import evaluate_message
from app.agent.self_correction import run_self_correction
from app.llm.gemini_client import generate_message
from app.models.profile_models import ScrapedProfile
from app.models.request_models import Tone
from app.models.response_models import OutreachMessage

# Set up logging to see the self-correction steps
logging.basicConfig(level=logging.INFO, format="%(message)s")

# A profile with strong specific evidence
PROFILE = ScrapedProfile(
    profile_url="https://linkedin.com/in/demo",
    name="Jane Demo",
    headline="ML Engineer | Building RAG systems",
    about="I work on retrieval-augmented generation and evaluation pipelines.",
    recent_activity=[
        "Shared a post: 'Why RAG evaluation is broken and how to fix it.'",
        "Commented on a post about embedding models.",
    ],
)

PRODUCT = (
    "OutreachIQ is an AI platform that personalizes sales outreach by "
    "evaluating profile data and grounding messages in concrete facts."
)

# A weak generic message that ignores the profile evidence
WEAK_MESSAGE = OutreachMessage(
    recipient_name="Jane",
    message=(
        "Hi Jane, I saw your impressive profile. "
        "We help companies achieve their goals using our AI platform. "
        "Would love to connect and show you a demo."
    ),
    reason_for_outreach="Jane works in tech.",
)

# A mock generator that returns the weak message on attempt 1,
# and calls the real Gemini API on attempt 2 (regeneration).
call_count = [0]


def demo_generator(prompt: str) -> OutreachMessage:
    call_count[0] += 1
    if call_count[0] == 1:
        logging.info("--- [Demo Generator] Attempt 1: Returning injected weak message ---")
        return WEAK_MESSAGE

    logging.info("--- [Demo Generator] Attempt %d: Calling real Gemini API ---", call_count[0])
    return generate_message(prompt)


def main() -> None:
    print("=" * 70)
    print("  OutreachIQ Phase 3 — Self-Correction Demo")
    print("=" * 70)
    print()

    try:
        result = run_self_correction(
            profile=PROFILE,
            product_description=PRODUCT,
            tone=Tone.CASUAL,
            generate_fn=demo_generator,
            evaluate_fn=evaluate_message,
        )
    except Exception as exc:
        print(f"\n[DEMO ERROR] {type(exc).__name__}: {exc}")
        return

    print("\n" + "=" * 70)
    print("  FINAL RESULT SUMMARY")
    print("=" * 70)
    print(f"Total Attempts : {result.attempt_count}")
    print(f"Improved       : {result.improved}")
    print(f"Final Score    : {result.final_evaluation.overall_score:.2f} / 10")
    print(f"Passed         : {result.final_evaluation.passed}")
    print("-" * 70)

    for record in result.history:
        print(f"\n[ATTEMPT {record.attempt}]")
        print(f"Message:")
        print(record.message.message)
        print(f"Score: {record.evaluation.overall_score:.2f}")
        if record.evaluation.feedback:
            print("Feedback:")
            print(record.evaluation.feedback)

    print("\n[BEST MESSAGE SELECTED]")
    print(result.final_message.message)
    print()


if __name__ == "__main__":
    main()
