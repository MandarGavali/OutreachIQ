# OutreachIQ Architecture

## Overview

OutreachIQ is an AI-powered LinkedIn outreach message generator.

The application accepts a profile URL, product/service description, and a
desired tone. A custom agent loop coordinates profile acquisition and
personalized message generation.

## Request Flow

```text
User
 │
 ├── POST /generate (JSON: profile_text or profile_url)
 ├── POST /generate-from-pdf (Multipart: single PDF file)
 └── POST /generate-batch-from-pdf (Multipart: multiple PDF files)
 │
 ▼
Pydantic Request Models (OutreachRequest / ProfileInput)
 │
 ▼
Custom Agent Core (OutreachAgent)
 │
 ├─── Turn 1: LLM → scrape_profile
 │                  │
 │                  ├── source='text' ───► TextProfileAdapter
 │                  ├── source='pdf'  ───► PDFProfileAdapter (via endpoint setup)
 │                  └── source='fixture' ─► URL validation → Cache → FixtureProfileAdapter
 │                                              │
 │                                         RawProfileData
 │                                              │
 │                                         normalize_profile()
 │                                              │
 │                                         ScrapedProfile
 │
 ├─── Turn 2: LLM → generate_message ─────► Self-Correction Orchestrator
 │                                              │
 │                                          Message Generation
 │                                              │
 │                                          Self-Correction Evaluator
 │                                              │
 │                                          Quality Gate
 │                                           ├── PASS → Final
 │                                           └── FAIL → Feedback → Regenerate → Evaluate
 │                                              │
 │                                         OutreachMessage
 │
 ├─── Turn 3: LLM → Final JSON response
 │
 ▼
OutreachMessage (validated Pydantic model)
 │
 ▼
FastAPI Response (Batch processing provides isolated failure handling & CSV export)
```

## CSV Export
A dedicated endpoint `POST /export-csv` is provided. The frontend can pass the successful `OutreachMessage` results from a batch to receive a downloadable CSV string via a StreamingResponse, decoupled from the initial generation phase.

## Legacy Infrastructure
The browser_manager and Playwright code paths exist for historical and experimental reference only. Production profile acquisition uses user-provided text or PDF input and does NOT perform unauthenticated LinkedIn DOM scraping.

## Limitations

- The application does not automatically send LinkedIn messages.
- The application does not perform mass automated outreach.

## Future Improvements

Potential future improvements include:

- Live public-profile data extraction
- Message quality scoring persistence
- Additional LLM providers
- Improved batch processing
- Persistent outreach history
- Authentication and user accounts
Additional LLM providers
Improved batch processing
Persistent outreach history
Authentication and user accounts