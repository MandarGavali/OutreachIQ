# OutreachIQ

## AI-Powered Personalized Outreach Agent

OutreachIQ is an AI-powered outreach assistant that transforms user-provided professional profile information into personalized, context-aware outreach messages.

Unlike a simple LLM wrapper that sends a prompt to Gemini and returns text, OutreachIQ is built as a structured AI application with:

* Profile acquisition and normalization
* Strongly typed data models
* Custom LLM agent orchestration
* Tool calling
* Prompt-driven message generation
* Independent LLM-based message evaluation
* Self-correction and regeneration
* Deterministic quality gating
* Best-attempt selection
* Batch PDF processing
* Per-file failure isolation
* CSV export
* REST APIs through FastAPI
* CLI demonstration workflows
* Unit, integration, regression, and end-to-end testing

The system is intentionally designed as a **human-in-the-loop outreach assistant**. It generates message drafts but does not automatically send LinkedIn messages or automate LinkedIn accounts.

---

# Table of Contents

* [Problem](#problem)
* [Solution](#solution)
* [What Makes OutreachIQ Different](#what-makes-outreachiq-different)
* [System Architecture](#system-architecture)
* [End-to-End Data Flow](#end-to-end-data-flow)
* [1. Profile Acquisition Layer](#1-profile-acquisition-layer)
* [2. Profile Parsing and Normalization](#2-profile-parsing-and-normalization)
* [3. Custom Agent Orchestration](#3-custom-agent-orchestration)
* [4. Message Generation](#4-message-generation)
* [5. Self-Correction and Evaluation](#5-self-correction-and-evaluation)
* [6. Quality Gate](#6-quality-gate)
* [7. Batch Processing and Failure Isolation](#7-batch-processing-and-failure-isolation)
* [8. CSV Export](#8-csv-export)
* [API](#api)
* [Tech Stack](#tech-stack)
* [Project Structure](#project-structure)
* [Installation](#installation)
* [Running the Application](#running-the-application)
* [CLI Demo](#cli-demo)
* [Testing](#testing)
* [Example](#example)
* [Responsible Use](#responsible-use)
* [Engineering Decisions](#engineering-decisions)
* [V1 → V2 Evolution](#v1--v2-evolution)
* [Current Limitations](#current-limitations)
* [Future Roadmap](#future-roadmap)
* [Learning Outcomes](#learning-outcomes)
* [Interview Explanation](#interview-explanation)
* [License](#license)

---

# Problem

Personalized outreach is difficult to do consistently.

A typical workflow requires a user to:

1. Find a prospect.
2. Read their professional profile.
3. Understand their role and background.
4. Identify something genuinely relevant.
5. Understand whether the sender's product is relevant.
6. Write an opening message.
7. Rewrite the message to sound natural.
8. Repeat the process for every prospect.

This creates a trade-off:

```text
More personalization
        ↓
More time per prospect
```

or:

```text
More prospects
        ↓
Less personalization
        ↓
Generic / spam-like outreach
```

OutreachIQ attempts to reduce this trade-off by using AI for the research-to-draft portion of the workflow.

---

# Solution

OutreachIQ accepts:

```text
Professional Profile Information
            +
Product / Service Description
            +
Desired Communication Tone
```

and produces:

```text
Personalized Outreach Message
            +
Reason for Personalization
            +
Structured Output
```

The important difference is that the LLM is not operating in isolation.

The application provides:

* Structured inputs
* Profile normalization
* Explicit tool boundaries
* Agent orchestration
* Output validation
* Independent evaluation
* Quality thresholds
* Regeneration
* Best-result selection
* Failure isolation

This makes the system more than a direct API wrapper around an LLM.

---

# What Makes OutreachIQ Different

A basic implementation would look like:

```text
User
  ↓
Prompt
  ↓
Gemini
  ↓
Message
```

OutreachIQ V2 instead follows:

```text
User
  ↓
Profile Acquisition
  ↓
Parsing
  ↓
Normalization
  ↓
Structured Profile
  ↓
Custom Agent
  ↓
Tool Calling
  ↓
Message Generation
  ↓
Independent Evaluation
  ↓
Quality Gate
  ├── Pass → Return
  │
  └── Fail → Regenerate
                 ↓
              Evaluate
                 ↓
          Select Best Attempt
                 ↓
               Return
```

The key engineering principle is:

> **Use the LLM for probabilistic reasoning and generation while keeping application control, validation, scoring, retry logic, and data flow deterministic.**

---

# System Architecture

```text
                         ┌──────────────────────────┐
                         │          USER            │
                         │                          │
                         │  Profile Text            │
                         │       OR                 │
                         │  Profile PDF             │
                         │                          │
                         │  Product Description     │
                         │  Tone                    │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │   PROFILE ACQUISITION    │
                         │                          │
                         │ TextProfileAdapter       │
                         │ PDFProfileAdapter        │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │         PARSER            │
                         │                          │
                         │ Raw Input → Fields       │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │       NORMALIZER          │
                         │                          │
                         │ Clean + Standardize      │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │     ScrapedProfile        │
                         │     Pydantic Model        │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │         CUSTOM OUTREACH AGENT       │
                    │                                     │
                    │      LLM Reasoning + Tool Calls     │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                         ┌──────────────────────────┐
                         │   MESSAGE GENERATOR      │
                         │                          │
                         │ Profile + Product + Tone │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │       GEMINI LLM         │
                         │                          │
                         │  Draft Message           │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │       EVALUATOR          │
                         │                          │
                         │ 6 Quality Dimensions     │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │      QUALITY GATE        │
                         │                          │
                         │ Score >= 7.0 ?           │
                         └────────────┬─────────────┘
                                      │
                         ┌────────────┴────────────┐
                         │                         │
                       PASS                       FAIL
                         │                         │
                         ▼                         ▼
                    Return Message          Regenerate
                                                   │
                                                   ▼
                                               Evaluate
                                                   │
                                                   ▼
                                           Best Attempt
                                                   │
                                                   ▼
                         ┌──────────────────────────┐
                         │   OutreachMessage        │
                         │   Pydantic Model         │
                         └────────────┬─────────────┘
                                      │
                         ┌────────────┴─────────────┐
                         │                          │
                         ▼                          ▼
                    JSON API                  CSV Export
```

---

# End-to-End Data Flow

The complete system can be understood as a sequence of transformations.

## Stage 1 — User Input

The user provides:

```text
Profile Source
Product / Service Description
Tone
```

The profile source can be:

```text
Raw Profile Text
```

or:

```text
User-Provided PDF
```

---

## Stage 2 — Profile Acquisition

The acquisition layer determines how the profile information should be obtained.

```text
Profile Input
     │
     ├── Text
     │     ↓
     │  Text Adapter
     │
     └── PDF
           ↓
       PDF Adapter
```

Both paths eventually produce profile text.

---

## Stage 3 — Parsing

Raw profile information is converted into meaningful fields.

For example:

```text
Raw Profile Text
        ↓
Name
Headline
About
Experience
Education
Other Relevant Context
```

Because exported profile PDFs are not guaranteed to follow a perfectly consistent structure, the parser uses heuristic extraction and fallback logic.

---

## Stage 4 — Normalization

The extracted information is cleaned and converted into a canonical representation.

```text
Raw / Noisy Data
      ↓
Parser
      ↓
Normalizer
      ↓
ScrapedProfile
```

The `ScrapedProfile` model becomes the internal contract used by the rest of the application.

This means downstream components do not need to understand whether the original profile came from text or PDF.

---

# 1. Profile Acquisition Layer

OutreachIQ V2 intentionally moved away from automated LinkedIn DOM scraping.

The system does not rely on:

* Automated LinkedIn login
* Browser sessions
* LinkedIn account automation
* DOM scraping
* Private profile access
* Automated message sending

Instead, profile information is explicitly supplied by the user.

## Supported Sources

### Text Input

The user can directly provide profile information as text.

```text
Name: Alex Rivera
Headline: Head of Growth
About: ...
Experience: ...
```

### PDF Input

The user can provide a PDF containing exported professional profile information.

For example, a user can use a platform's profile export / "Save to PDF" capability and upload the resulting document.

The pipeline then becomes:

```text
PDF
 ↓
Temporary Processing
 ↓
Text Extraction
 ↓
Parser
 ↓
Normalizer
 ↓
ScrapedProfile
```

Temporary PDF files are removed after processing where required by the acquisition workflow.

Profile information is not persisted as part of the PDF acquisition workflow.

---

# 2. Profile Parsing and Normalization

The acquisition layer separates three concerns:

```text
Acquisition
    ↓
Parsing
    ↓
Normalization
```

This separation is important because profile input is inherently unstructured.

For example, two PDFs may represent the same information differently:

```text
PDF A
Name
Headline
About
Experience
```

while another may contain:

```text
About
Experience
Name
Headline
```

The parser therefore uses heuristics and fallback logic rather than assuming one rigid layout.

The result is converted into a canonical `ScrapedProfile`.

Conceptually:

```python
ScrapedProfile(
    name=...,
    headline=...,
    about=...,
    experience=...,
    education=...,
    ...
)
```

The exact fields are defined by the Pydantic models in the repository.

---

# 3. Custom Agent Orchestration

One of the main V2 improvements is the custom agent loop.

OutreachIQ does not simply execute a fixed chain of:

```text
Profile → Generator
```

Instead, the application contains a custom orchestration layer responsible for managing the LLM interaction and tool execution.

## Agent Loop

```text
User Request
     ↓
LLM
     ↓
Does the model request a tool?
     │
     ├── No
     │    ↓
     │  Final Response
     │
     └── Yes
          ↓
      Validate Tool Arguments
          ↓
      Execute Tool
          ↓
      Add Tool Result
          ↓
      Conversation History
          ↓
      LLM Again
          ↓
      Continue
```

The loop is bounded by a maximum number of turns.

This prevents an uncontrolled agent execution cycle.

The current implementation uses a maximum of **6 turns**.

---

## Why a Custom Agent Loop?

Using a custom loop provides explicit control over:

* Tool execution
* Tool argument validation
* Conversation state
* Maximum turns
* Malformed model responses
* Error handling
* Final response handling

It also makes the agent behavior easier to test.

The architecture therefore separates:

```text
LLM Reasoning
```

from:

```text
Application Control
```

---

# 4. Message Generation

The message generator receives the structured profile context together with the user's campaign information.

Conceptually:

```text
ScrapedProfile
      +
Product Description
      +
Tone
      ↓
Prompt Builder
      ↓
Gemini
      ↓
Draft Outreach Message
```

The generation prompt instructs the model to prioritize:

* Genuine personalization
* Relevance
* Specificity
* Natural language
* Factual accuracy
* Non-spammy communication

The model should not invent profile facts that are not supported by the provided information.

---

# 5. Self-Correction and Evaluation

The self-correction layer is one of the most important components of OutreachIQ V2.

A normal LLM application might do:

```text
Generate
  ↓
Return
```

OutreachIQ instead performs:

```text
Generate
  ↓
Evaluate
  ↓
Quality Gate
  ↓
Pass → Return
```

or:

```text
Generate
  ↓
Evaluate
  ↓
Fail
  ↓
Feedback
  ↓
Regenerate
  ↓
Evaluate Again
```

---

## Evaluation Dimensions

The evaluator scores the generated message across six dimensions:

1. **Personalization**
2. **Relevance**
3. **Specificity**
4. **Naturalness**
5. **Non-spamminess**
6. **Factuality**

Each dimension is evaluated on a 0–10 scale.

The evaluator also provides feedback that can be passed back into the generation process when regeneration is required.

---

# 6. Quality Gate

The evaluator's output is not directly trusted as the final decision.

Python-side application logic controls the quality gate.

The configured threshold is:

```text
7.0 / 10
```

The flow is:

```text
Generated Message
       ↓
Evaluator
       ↓
Overall Score
       │
       ├── >= 7.0
       │      ↓
       │    Accept
       │
       └── < 7.0
              ↓
          Regenerate
              ↓
           Evaluate
```

This is an important architectural distinction.

The LLM performs:

```text
Generation
Evaluation
Feedback
```

while application code performs:

```text
Threshold comparison
Retry control
Attempt tracking
Best-result selection
```

---

## Best Attempt Selection

When multiple generation attempts occur, OutreachIQ does not blindly return the latest response.

The system tracks valid attempts and selects the highest-scoring valid result.

Conceptually:

```text
Attempt 1 → 6.4
Attempt 2 → 7.8
Attempt 3 → 7.2

Final → Attempt 2
```

This makes the regeneration process a controlled optimization loop rather than simply a retry mechanism.

---

# 7. Batch Processing and Failure Isolation

OutreachIQ supports multiple profile PDFs through:

```http
POST /generate-batch-from-pdf
```

The current batch endpoint supports up to **10 PDF files**.

The important design decision is **failure isolation**.

Without isolation:

```text
PDF 1 ✓
PDF 2 ✓
PDF 3 ✗
     ↓
Entire batch fails
```

OutreachIQ instead handles files independently:

```text
PDF 1 → Success
PDF 2 → Success
PDF 3 → Failure
PDF 4 → Success
PDF 5 → Success
```

The failed file is recorded while processing continues.

For example:

```json
{
  "total": 5,
  "successful": 4,
  "failed": 1
}
```

A corrupted or empty PDF can therefore produce a `ProfileAcquisitionError` for that individual item without crashing the entire batch request.

---

# 8. CSV Export

Successful outreach results can be exported through:

```http
POST /export-csv
```

The endpoint accepts structured `OutreachMessage` results and generates a CSV response using FastAPI's `StreamingResponse`.

Conceptually:

```text
OutreachMessage[]
       ↓
CSV Exporter
       ↓
StreamingResponse
       ↓
CSV
```

This allows generated messages to be reviewed and used outside the API.

---

# API

OutreachIQ exposes its functionality through FastAPI.

## `POST /generate`

Generates an outreach message from raw profile text.

### Request

```json
{
  "profile_text": "Name: Alex Rivera\nHeadline: Head of Growth...",
  "product_description": "We build an AI-powered outreach platform.",
  "tone": "casual"
}
```

### Flow

```text
JSON Request
    ↓
Pydantic Validation
    ↓
Profile Acquisition
    ↓
Agent
    ↓
Generation
    ↓
Evaluation
    ↓
Quality Gate
    ↓
OutreachMessage
    ↓
JSON Response
```

---

## `POST /generate-from-pdf`

Generates an outreach message from a single uploaded PDF.

### Request

`multipart/form-data`

Parameters:

```text
profile_pdf
product_description
tone
```

### Flow

```text
PDF
 ↓
PDFProfileAdapter
 ↓
Parser
 ↓
Normalizer
 ↓
ScrapedProfile
 ↓
Agent
 ↓
Generator
 ↓
Evaluator
 ↓
OutreachMessage
```

---

## `POST /generate-batch-from-pdf`

Processes multiple profile PDFs.

### Request

`multipart/form-data`

Parameters:

```text
files
product_description
tone
```

Maximum number of PDFs:

```text
10
```

### Response

The endpoint returns structured batch information including:

* Total files
* Successful files
* Failed files
* Per-file results
* Per-file errors where applicable

This endpoint demonstrates failure isolation rather than treating a batch as one indivisible operation.

---

## `POST /export-csv`

Converts successful `OutreachMessage` objects into a downloadable CSV response.

The endpoint uses FastAPI `StreamingResponse` to return the generated CSV.

---

# Tech Stack

| Technology                    | Purpose                             |
| ----------------------------- | ----------------------------------- |
| Python 3.13                   | Core application                    |
| FastAPI                       | REST API and routing                |
| Pydantic                      | Data validation and typed contracts |
| Pydantic Settings             | Environment configuration           |
| Google Gemini                 | LLM generation and evaluation       |
| PyPDF                         | PDF text extraction                 |
| Pytest                        | Automated testing                   |
| CSV / Python standard library | Result export                       |
| Git / GitHub                  | Version control                     |

---

# Project Structure

```text
outreachiq/
│
├── app/
│   │
│   ├── agent/
│   │   ├── ...
│   │   └── # Custom agent orchestration,
│   │       # tool calling and evaluation
│   │
│   ├── api/
│   │   ├── ...
│   │   └── # FastAPI routes
│   │
│   ├── export/
│   │   └── # CSV generation
│   │
│   ├── generator/
│   │   ├── ...
│   │   └── # Prompt construction,
│   │       # message generation and tone logic
│   │
│   ├── models/
│   │   ├── ...
│   │   └── # Pydantic request,
│   │       # response and evaluation models
│   │
│   ├── scraper/
│   │   ├── ...
│   │   └── # Text/PDF acquisition,
│   │       # parsing and normalization
│   │
│   ├── config.py
│   └── main.py
│
├── docs/
│   ├── architecture.md
│   └── ethical_use.md
│
├── scripts/
│   └── final_demo.py
│
├── tests/
│   ├── ...
│   └── # Unit, integration,
│       # regression and E2E tests
│
├── examples/
│   └── ...
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

# Installation

## 1. Clone the Repository

```bash
git clone <repository-url>
cd outreachiq
```

---

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux

```bash
python -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Add the required Google Gemini API key:

```env
GOOGLE_API_KEY=your_api_key_here
```

Do not commit `.env` to Git.

---

# Running the Application

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

FastAPI Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

ReDoc:

```text
http://127.0.0.1:8000/redoc
```

---

# CLI Demo

OutreachIQ includes a CLI demonstration script for testing the complete pipeline without manually interacting with the API.

## Text Input

```bash
python -m scripts.final_demo --source text
```

## Single PDF

```bash
python -m scripts.final_demo --source pdf --pdf "examples/sample_profile.pdf"
```

## Multiple PDFs

```bash
python -m scripts.final_demo --source pdf --pdf "C:\profile1.pdf" "C:\profile2.pdf"
```

The CLI is useful for validating the complete acquisition → agent → generation → evaluation pipeline.

---

# Real-World Validation

The final V2 pipeline was tested with a real user-provided LinkedIn profile PDF.

The actual execution followed:

```text
LinkedIn Profile PDF
        ↓
PDFProfileAdapter
        ↓
PDF Parser
        ↓
Normalization
        ↓
ScrapedProfile
        ↓
Custom Outreach Agent
        ↓
Gemini Generation
        ↓
Gemini Evaluation
        ↓
Quality Score: 9.00
        ↓
Accepted
```

The message passed the quality gate in **one attempt**.

This validated the complete pipeline rather than testing only isolated components.

---

# Testing

Testing is a major part of the V2 implementation.

The test suite covers multiple layers:

```text
                 Test Suite
                     │
        ┌────────────┼─────────────┐
        │            │             │
        ▼            ▼             ▼
      Unit       Integration       E2E
        │            │             │
        ▼            ▼             ▼
   Components      APIs        Full Pipeline
```

Tests cover areas including:

### Model Validation

* Valid request handling
* Invalid request rejection
* Response validation
* Evaluation model validation

### Profile Acquisition

* Text acquisition
* PDF acquisition
* Parser behavior
* Normalization
* Empty input
* Invalid/corrupted PDF handling

### Agent

* Tool calling
* Agent loop behavior
* Malformed LLM responses
* Maximum turn limits
* Final response handling

### Self-Correction

* Evaluation scoring
* Threshold behavior
* Regeneration
* Evaluator feedback
* Best-attempt selection
* Factuality failures
* Generic personalization failures

### API

* Route validation
* HTTP status codes
* JSON responses
* PDF uploads
* Batch processing
* CSV export

### Regression

The V2 implementation includes regression coverage to ensure that the revamped architecture does not silently break existing behavior.

Run the complete suite with:

```bash
python -m pytest -v
```

---

# Responsible Use

OutreachIQ follows a **human-in-the-loop** design.

## No Automated Sending

OutreachIQ generates message drafts.

It does not:

* Send LinkedIn messages
* Send connection requests
* Automatically interact with LinkedIn accounts
* Perform mass outreach

The user remains responsible for reviewing and sending the final message.

---

## No Automated LinkedIn DOM Scraping

The V2 architecture deliberately removed the earlier Playwright-based LinkedIn scraping approach.

The final system does not depend on:

* Automated browser sessions
* LinkedIn login automation
* DOM scraping
* Session-cookie handling
* Private profile access
* Automated account actions

Instead, the user supplies the profile information explicitly through text or a profile PDF.

This makes the profile acquisition architecture simpler, more controlled, and easier to reason about.

---

## Data Privacy

The PDF acquisition workflow uses temporary processing where required.

Uploaded PDFs are processed to extract the necessary profile information and are deleted after the acquisition workflow completes.

The profile acquisition pipeline does not intentionally persist the uploaded PDF or create a permanent profile database.

---

# Engineering Decisions

## Why not simply call Gemini?

A minimal implementation would be:

```python
response = gemini.generate_content(prompt)
```

That technically produces an AI application, but it leaves important engineering problems unsolved.

OutreachIQ adds:

```text
Typed Inputs
     ↓
Profile Acquisition
     ↓
Normalization
     ↓
Agent Orchestration
     ↓
Tool Calling
     ↓
Generation
     ↓
Independent Evaluation
     ↓
Quality Gate
     ↓
Regeneration
     ↓
Best Attempt
     ↓
Typed Output
```

This demonstrates engineering around an LLM rather than only API consumption.

---

## Why Pydantic?

LLMs are probabilistic.

Application boundaries should not be.

Pydantic creates explicit contracts between components.

```text
Untrusted Input
      ↓
Pydantic
      ↓
Validated Data
      ↓
Application
```

The same principle applies to generated output.

```text
LLM Output
     ↓
Validation
     ↓
OutreachMessage
```

---

## Why a Separate Evaluator?

Generation and evaluation are treated as separate responsibilities.

The generator asks:

> What message should be written?

The evaluator asks:

> How good is this message according to the defined criteria?

This separation enables a controlled feedback loop.

```text
Generator
    ↓
Draft
    ↓
Evaluator
    ↓
Feedback
    ↓
Generator
```

---

## Why Keep the Quality Gate in Python?

The LLM provides the score, but Python controls what happens with that score.

For example:

```python
if score >= 7.0:
    return best_attempt

regenerate()
```

This prevents the model from being responsible for its own retry policy.

Application code controls:

* Thresholds
* Retry limits
* Attempt tracking
* Selection logic
* Failure behavior

---

## Why Failure Isolation?

Batch processing should not behave like a single monolithic operation.

If one input is invalid:

```text
Valid Input 1 → Success
Valid Input 2 → Success
Invalid Input 3 → Failure
Valid Input 4 → Success
```

The correct behavior is to preserve the successful results.

This makes the system more resilient and production-oriented.

---

# V1 → V2 Evolution

OutreachIQ started as a relatively simple LLM-powered outreach generator.

The initial concept was approximately:

```text
Profile
   +
Product Description
   +
Tone
   ↓
LLM
   ↓
Message
```

V2 evolved this into a complete AI application.

## V1

```text
Input
 ↓
LLM
 ↓
Output
```

## V2

```text
                    ┌──────────────────┐
                    │ Profile Input    │
                    └────────┬─────────┘
                             │
                             ▼
                    Profile Acquisition
                             │
                             ▼
                         Parsing
                             │
                             ▼
                       Normalization
                             │
                             ▼
                     ScrapedProfile
                             │
                             ▼
                      Custom Agent
                             │
                             ▼
                      Tool Calling
                             │
                             ▼
                    Message Generator
                             │
                             ▼
                       Gemini LLM
                             │
                             ▼
                        Evaluator
                             │
                             ▼
                      Quality Gate
                       /        \
                    PASS        FAIL
                     │            │
                     │       Regenerate
                     │            │
                     │       Re-evaluate
                     │            │
                     └──────┬─────┘
                            ▼
                     Best Valid Result
                            │
                            ▼
                    OutreachMessage
                       /          \
                    JSON          CSV
```

---

# Major V2 Engineering Improvements

## 1. Unstructured → Structured Data

Profile PDFs are inherently messy.

The system converts:

```text
Unstructured PDF Text
        ↓
Heuristic Parsing
        ↓
Normalization
        ↓
ScrapedProfile
```

This provides a stable internal representation.

---

## 2. Custom Agent Loop

Instead of depending entirely on a pre-built agent abstraction, OutreachIQ implements explicit orchestration logic.

This gives control over:

* Tool calling
* Arguments
* Conversation history
* Turn limits
* Errors
* Final responses

---

## 3. Self-Correction

The first generated message is not automatically accepted.

```text
Generate
 ↓
Score
 ↓
Improve if necessary
 ↓
Score Again
 ↓
Return Best
```

This provides a measurable quality-control mechanism.

---

## 4. Deterministic Quality Control Around Probabilistic AI

A central architectural principle is:

```text
LLM
 ↓
Probabilistic Output
 ↓
Python Validation
 ↓
Python Scoring Logic
 ↓
Python Retry Control
 ↓
Deterministic Application Behavior
```

The LLM provides intelligence.

The application provides control.

---

## 5. Batch Failure Isolation

Individual failures are isolated so that one invalid profile does not terminate the entire batch.

---

## 6. Comprehensive Testing

The project includes testing across:

```text
Unit
Integration
Regression
End-to-End
```

This is important because AI applications can fail at multiple boundaries:

```text
Input
 ↓
Parser
 ↓
Agent
 ↓
LLM
 ↓
Evaluator
 ↓
API
 ↓
Export
```

---

# Current Limitations

OutreachIQ is intentionally scoped as an AI-assisted outreach generation system.

Current limitations include:

### Profile Acquisition

The system relies on user-provided profile text or PDFs.

It does not automatically retrieve LinkedIn profiles.

### PDF Parsing

PDF extraction depends on the document containing a usable text layer.

Image-only PDFs may require OCR.

### LLM Dependency

Message generation and evaluation depend on the configured Google Gemini API.

### LLM Evaluation

The evaluator is itself an LLM-based component, meaning its judgment is not equivalent to a deterministic human evaluation.

The application therefore combines LLM evaluation with deterministic threshold and retry logic rather than treating the evaluator as an absolute source of truth.

---

# Future Roadmap

Potential future improvements include:

## Frontend

A dedicated web interface for:

* Profile upload
* Product/service configuration
* Tone selection
* Generated message review
* Quality score visualization
* Batch management

---

## Advanced Research

Expand the research layer with additional permitted sources:

```text
Profile
   ↓
Company Context
   ↓
Public Professional Context
   ↓
Relevance Analysis
```

---

## Better Evaluation

Introduce more sophisticated evaluation capabilities:

* Custom scoring rubrics
* Human feedback
* Evaluation datasets
* Regression benchmarks
* Prompt/version comparison
* Automated quality reports

---

## Background Processing

Large batches could eventually be moved to asynchronous processing using a background job architecture.

For example:

```text
API
 ↓
Job Queue
 ↓
Worker
 ↓
Profile Processing
 ↓
Generation
 ↓
Evaluation
 ↓
Result Store
```

---

## Persistence

A future production version could store:

* Outreach campaigns
* Generated messages
* Evaluation scores
* User feedback
* Prompt versions
* Generation history

This would allow OutreachIQ to evolve from a message generator into a complete outreach intelligence platform.

---

# Learning Outcomes

Building OutreachIQ provides practical experience with:

* LLM application architecture
* AI agents
* Custom agent orchestration
* Tool calling
* Prompt engineering
* Structured generation
* Pydantic
* FastAPI
* PDF processing
* Unstructured data extraction
* Data normalization
* Self-correction loops
* LLM evaluation
* Quality gates
* Retry strategies
* Best-result selection
* Batch processing
* Failure isolation
* REST API design
* CSV generation
* Automated testing
* Integration testing
* End-to-end testing
* Responsible AI design

The larger lesson is how to turn an LLM API into a structured software system.

---

# Interview Explanation

A concise technical explanation:

> **OutreachIQ is an AI-powered personalized outreach agent that converts user-provided professional profile information into context-aware outreach messages. I built a custom agent orchestration loop instead of using a simple prompt-to-LLM architecture. Profile text or exported PDFs first pass through an acquisition, parsing, and normalization pipeline into a strongly typed `ScrapedProfile`. The custom agent then orchestrates message generation using Gemini. Every generated message is independently evaluated across personalization, relevance, specificity, naturalness, non-spamminess, and factuality. If the score is below a 7.0 threshold, the system regenerates the message using evaluator feedback and ultimately selects the highest-scoring valid attempt. The system also supports batch PDF processing with per-file failure isolation, CSV export, FastAPI endpoints, and comprehensive unit, integration, regression, and end-to-end testing. I intentionally removed automated LinkedIn scraping and message sending and kept the system human-in-the-loop.**

---

# Architecture in One Diagram

For someone who wants to understand the entire project quickly:

```text
                    OUTREACHIQ V2
                         │
                         ▼
              ┌─────────────────────┐
              │    USER PROVIDES    │
              │                     │
              │ Profile Text / PDF  │
              │ Product Description │
              │ Tone                │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ PROFILE ACQUISITION │
              │                     │
              │ Text Adapter        │
              │ PDF Adapter         │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │       PARSER        │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │     NORMALIZER      │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   ScrapedProfile    │
              │   Pydantic Model    │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   CUSTOM AGENT      │
              │                     │
              │ LLM + Tool Calling │
              │ Max 6 Turns         │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ MESSAGE GENERATOR   │
              │                     │
              │ Profile + Product   │
              │ + Tone              │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │    GEMINI LLM       │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │     EVALUATOR       │
              │                     │
              │ Personalization     │
              │ Relevance           │
              │ Specificity         │
              │ Naturalness         │
              │ Non-spamminess      │
              │ Factuality          │
              └──────────┬──────────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Score >= 7.0? │
                 └───────┬───────┘
                    ┌────┴────┐
                   YES        NO
                    │          │
                    ▼          ▼
                 ACCEPT     REGENERATE
                    │          │
                    │          ▼
                    │       EVALUATE
                    │          │
                    └────┬─────┘
                         │
                         ▼
                ┌──────────────────┐
                │ Best Valid Result│
                └────────┬─────────┘
                         │
                         ▼
                ┌──────────────────┐
                │ OutreachMessage  │
                └────────┬─────────┘
                         │
                   ┌─────┴─────┐
                   ▼           ▼
                  JSON        CSV
                   │           │
                   └─────┬─────┘
                         ▼
                  HUMAN REVIEW
                         │
                         ▼
                 MANUAL OUTREACH
```

---

# Project Status

OutreachIQ V2 has been implemented and shipped to the `main` branch.

The final architecture includes:

* Text profile acquisition
* PDF profile acquisition
* Profile parsing
* Profile normalization
* Canonical `ScrapedProfile`
* Custom agent orchestration
* Tool calling
* Gemini message generation
* LLM-based evaluation
* Self-correction
* Quality thresholding
* Best-attempt selection
* Batch PDF processing
* Failure isolation
* CSV export
* FastAPI REST API
* CLI demonstration
* Unit testing
* Integration testing
* Regression testing
* End-to-end testing

The final implementation intentionally removed the legacy Playwright/LinkedIn DOM-scraping artifacts and keeps profile acquisition based on information explicitly supplied by the user.

---

# License

This project is licensed under the MIT License.

See the `LICENSE` file for details.

---

# Author

**Mandar**

AI & Data Science Engineering Student

GitHub: `<your-github-profile>`

LinkedIn: `<your-linkedin-profile>`

---

## Final Principle

OutreachIQ is not designed to send more automated messages.

It is designed to help a human produce **more relevant, personalized, and context-aware outreach with less manual effort**.

The engineering objective is equally important:

> **Keep the LLM responsible for intelligence and generation, while keeping the application responsible for structure, validation, evaluation, control, and reliability.**
> :::
