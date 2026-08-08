# OutreachIQ Architecture

## Overview

OutreachIQ is an AI-powered LinkedIn outreach message generator.

The application accepts profile information, product/service
information, and a desired tone. It uses a LangChain agent to
coordinate profile parsing and personalized message generation.

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
LangChain Agent
 │
 ├───────────────┐
 ▼               ▼
Scrape Profile   Generate Outreach
 Tool             Tool
 │               │
 ▼               ▼
Parser       Message Builder
 │               │
 ▼               ▼
ScrapedProfile   Gemini LLM
 │               │
 └───────┬───────┘
         ▼
   OutreachMessage
         │
         ▼
   FastAPI Response



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