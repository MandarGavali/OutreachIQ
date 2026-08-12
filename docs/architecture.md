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
 ▼
FastAPI
 │
 ▼
Pydantic OutreachRequest
 │
 ▼
Custom Agent Core (OutreachAgent)
 │
 ├─── Turn 1: LLM → scrape_profile ──────► ProfileScraper
 │                                              │
 │                                         ScrapedProfile
 │                                              │
 ├─── Turn 2: LLM → generate_message ─────► MessageBuilder → Gemini LLM
 │                                              │
 │                                         OutreachMessage
 │
 ├─── Turn 3: LLM → Final JSON response
 │
 ▼
OutreachMessage (validated Pydantic model)
 │
 ▼
FastAPI Response
```


Current Limitations:

Profile input currently uses pasted profile text.
LinkedIn authentication/session scraping is not implemented.
The application does not automatically send LinkedIn messages.
The application does not perform mass automated outreach.
Future Improvements



Potential future improvements include:

More robust profile parsing
Public-profile data extraction where appropriate
Better personalization evaluation
Message quality scoring
Additional LLM providers
Improved batch processing
Persistent outreach history
Authentication and user accounts