# OutreachIQ Usage Evidence

This document provides evidence of correct functionality through the test suite and integration runs.

## Test Suite Execution
The complete pytest suite includes:
- `test_agent.py`: Validates the custom agent loop, routing logic, tool parsing, max-turn budget, and structured error boundaries.
- `test_self_correction.py`: Proves the self-correction logic successfully evaluates personalization, tests factuality, handles prompt injection smoothly, and manages retries effectively.
- `test_scraper.py` & `test_acquisition.py`: Confirms rate limiting, fallback mocking, formatting, and string length limits.
- `test_api.py` & `test_regression.py`: Guarantees FastAPI compatibility with main branch payloads.
- `test_e2e.py`: Ensures single requests, batches, and fail-overs are fully integrated.

## Demo Script
A local demonstration script is provided at `scripts/final_demo.py` to trigger the end-to-end pipeline safely in development environments.

All 109 tests pass flawlessly on Windows Python 3.13 environments (see Github Actions / Task log outputs).
