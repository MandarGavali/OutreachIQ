"""
Final E2E Demo for OutreachIQ V2.

Run:
    python -m scripts.final_demo

This script runs the entire OutreachIQ pipeline locally for a single URL.
It uses the default agent, scraper, generator, and evaluator logic.

Note: Requires GOOGLE_API_KEY to be set in the .env file.
If the API key is not set, it will fail gracefully.
"""

import os
import sys
import logging
from pprint import pprint
from dotenv import load_dotenv

from app.agent.agent_core import generate_outreach
from app.models.request_models import OutreachRequest, Tone

def main():
    load_dotenv()
    if not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: GOOGLE_API_KEY is not set in the environment.")
        print("Please set it in your .env file to run the final demo.")
        sys.exit(1)

    # We will use the built-in FixtureProfileAdapter URL for Bob
    # This guarantees the scraper will return a strong profile
    # even without LinkedIn authentication.
    profile_url = "https://linkedin.com/in/bob"
    product_desc = (
        "OutreachIQ is an AI-powered platform that helps sales teams generate "
        "personalized, non-spammy outreach messages grounded in real profile data."
    )
    tone = Tone.CASUAL

    print("========================================")
    print("       OUTREACHIQ V2 DEMO")
    print("========================================")
    print("\nInput")
    print("-----")
    print(f"Profile: {profile_url}")
    print(f"Product: {product_desc}")
    print(f"Tone:    {tone.value}")
    print("\nAgent & Self-Correction")
    print("-----------------------")
    print("Starting agent loop... (check logs for details)")
    
    # We set up logging so the user can see the tool calls and self-correction attempts
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    req = OutreachRequest(
        profile_url=profile_url,
        product_description=product_desc,
        tone=tone
    )
    
    try:
        result = generate_outreach(req)
        
        print("\n========================================")
        print("       FINAL RESULT SUMMARY")
        print("========================================")
        print("\nFinal Message")
        print("-------------")
        print(f"To: {result.recipient_name}\n")
        print(result.message)
        
        print("\nReason for Outreach")
        print("-------------------")
        print(result.reason_for_outreach)
        
        print("\n========================================")
        
    except Exception as e:
        print(f"\n[DEMO ERROR] Pipeline failed: {e}")

if __name__ == "__main__":
    main()
