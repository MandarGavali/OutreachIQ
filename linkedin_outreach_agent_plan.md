# LinkedIn Outreach AI Agent — Complete 10-Day Build Plan

---

## 1. PROJECT OVERVIEW

**Name:** OutreachIQ (working name — change if you want)

**One-line pitch:** An AI agent that takes a LinkedIn profile and your product description, and generates a personalized, non-spammy outreach message referencing something real from that person's profile.

**What it explicitly does NOT do:** Auto-send messages, mass automate outreach, or scrape private data. This is intentional — it keeps you clear of LinkedIn ToS issues around automation, and it's an honest product decision you can defend in an interview.

**Target user:** Freelancers, founders, recruiters, sales people doing manual LinkedIn outreach who want better first messages, faster.

---

## 2. WHAT YOU ARE LEARNING / DEMONSTRATING

| Skill | Where it shows up |
|---|---|
| AI Agents + tool calling | Agent decides to call the scraper tool, then the message generator |
| Prompt engineering | Tone variation (formal/casual/technical), few-shot examples for good vs bad outreach |
| Pydantic | Every input and output strictly validated |
| FastAPI | Clean REST API serving the whole thing |
| Web scraping (ethical, public-data-only) | Extracting name, headline, recent activity from public profile pages |
| Structured output | CSV generation from validated Pydantic models |
| Rate limiting / responsible design | Respecting LinkedIn's terms, adding delays, no mass automation |
| Product thinking | Deciding what NOT to build (auto-send) and explaining why |

---

## 3. COMPLETE DIRECTORY STRUCTURE

```
outreachiq/
│
├── .env                              # API keys (OpenAI/Gemini), config
├── .env.example                      # Template for others to set up
├── .gitignore
├── README.md                         # Full project readme (section 5 below)
├── requirements.txt
├── docker-compose.yml                # If you containerize (optional, stretch goal)
│
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app entrypoint
│   ├── config.py                     # Settings, env var loading (pydantic-settings)
│   │
│   ├── models/                       # All Pydantic schemas
│   │   ├── __init__.py
│   │   ├── request_models.py         # OutreachRequest, BatchRequest
│   │   ├── response_models.py        # OutreachMessage, BatchResponse
│   │   └── profile_models.py         # ScrapedProfile (raw scraped data shape)
│   │
│   ├── scraper/                      # Tool 1 — profile data extraction
│   │   ├── __init__.py
│   │   ├── profile_scraper.py        # Core scraping logic
│   │   ├── parser.py                 # HTML parsing → structured data
│   │   └── rate_limiter.py           # Delay/throttling logic (ethical scraping)
│   │
│   ├── agent/                        # The AI agent itself
│   │   ├── __init__.py
│   │   ├── tools.py                  # Tool definitions (scrape_profile, generate_message)
│   │   ├── agent_core.py             # Agent orchestration logic
│   │   └── prompts.py                # All system prompts, few-shot examples
│   │
│   ├── generator/                    # Message generation logic
│   │   ├── __init__.py
│   │   ├── message_builder.py        # Builds prompt from profile + product info
│   │   └── tone_templates.py         # Formal/casual/technical tone definitions
│   │
│   ├── export/                       # Output handling
│   │   ├── __init__.py
│   │   └── csv_exporter.py           # Converts validated results → CSV
│   │
│   └── api/
│       ├── __init__.py
│       └── routes.py                 # All FastAPI endpoints
│
├── tests/                            # Basic tests (even simple ones help)
│   ├── __init__.py
│   ├── test_scraper.py
│   ├── test_agent.py
│   └── test_models.py
│
├── examples/                         # Sample inputs/outputs for demo
│   ├── sample_input.json
│   └── sample_output.csv
│
├── scripts/
│   └── demo_run.py                   # Standalone script to demo without API
│
└── docs/
    ├── architecture.md               # Architecture diagram + explanation
    └── ethical_use.md                # Your ToS-respecting design decisions
```

---

## 4. ARCHITECTURE FLOW

```
User Input (LinkedIn URL + product info + tone)
              │
              ▼
     ┌─────────────────┐
     │  Pydantic       │  ← Validates request shape
     │  Request Model  │
     └────────┬────────┘
              │
              ▼
     ┌─────────────────────────┐
     │      AI Agent            │
     │  (decides tool sequence) │
     └────────┬─────────────────┘
              │
     ┌────────┴─────────┐
     ▼                  ▼
┌──────────┐    ┌──────────────┐
│  Tool 1:  │    │   Tool 2:    │
│  Scraper  │───▶│   Message    │
│  (public  │    │   Generator  │
│  profile  │    │   (LLM call) │
│  data)    │    │              │
└──────────┘    └──────┬───────┘
                        │
                        ▼
              ┌──────────────────┐
              │  Pydantic         │
              │  Response Model   │  ← Validates output shape
              └────────┬──────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  CSV Exporter    │
              └────────┬─────────┘
                        │
                        ▼
                  Final CSV file
```

---

## 5. README.md (write this early, refine at the end)

```markdown
# OutreachIQ — AI-Powered LinkedIn Outreach Message Generator

OutreachIQ is an AI agent that generates personalized, non-spammy 
LinkedIn outreach messages by analyzing public profile information 
and your product/service context.

## The Problem

Freelancers, founders, and recruiters spend hours writing outreach 
messages manually — and most of them still read like generic spam. 
OutreachIQ generates first-touch messages that reference something 
specific and real from the recipient's profile, making outreach feel 
human rather than automated.

## What This Is NOT

This tool does not automate sending messages, does not scrape private 
data, and does not mass-spam LinkedIn. It generates message *drafts* 
from public profile information — a human still reviews and sends 
each one manually. This is a deliberate design decision to respect 
LinkedIn's Terms of Service around automation.

## How It Works

1. You provide a public LinkedIn profile URL, your product/service 
   description, and a desired tone (formal/casual/technical)
2. An AI agent extracts public profile information (name, headline, 
   recent public activity)
3. The agent generates a personalized message referencing specific 
   details from the profile
4. Output is validated and exported as a CSV you can review and use

## Tech Stack

- **FastAPI** — backend API
- **LangChain / OpenAI (or Gemini)** — LLM orchestration  
- **Pydantic** — strict input/output validation
- **BeautifulSoup / Playwright** — ethical public data extraction
- **Pandas** — CSV export

## Architecture

See `docs/architecture.md` for the full flow diagram and design 
decisions.

## Setup

\`\`\`bash
git clone <repo>
cd outreachiq
pip install -r requirements.txt
cp .env.example .env
# Add your API key to .env
uvicorn app.main:app --reload
\`\`\`

## API Usage

\`\`\`bash
curl -X POST http://localhost:8000/generate \\
  -H "Content-Type: application/json" \\
  -d '{
    "profile_url": "https://linkedin.com/in/example",
    "product_description": "AI-powered resume screening tool for recruiters",
    "tone": "casual"
  }'
\`\`\`

## Ethical Use

This project respects LinkedIn's public data boundaries and does not 
perform automated mass actions. See `docs/ethical_use.md` for the 
full reasoning behind these design choices.

## Author

Built by [Your Name] — [LinkedIn] — [GitHub]
```

---

## 6. THE 10-DAY PLAN

### **Day 1 — Foundation + Pydantic Models**
**Goal:** All data shapes defined before any logic is written.

- Set up project structure exactly as above
- Write `models/request_models.py`, `response_models.py`, `profile_models.py`
- Every field validated — required vs optional, string length limits, tone as an Enum (not free string)
- Write `config.py` for env var management using `pydantic-settings`
- Milestone: Run a script that creates a fake `OutreachRequest` and validates it, confirm errors trigger correctly for bad input

### **Day 2 — Scraper Foundation**
**Goal:** Extract structured data from a public LinkedIn profile page.

- Research: LinkedIn blocks most scraping aggressively. Decide your approach — either (a) use a headless browser (Playwright) with careful rate limiting, or (b) for a safer MVP, accept manually pasted profile text/bio instead of live scraping
- **Recommended for your timeline:** Start with option (b) — user pastes profile text/headline/bio directly, OR you scrape only if the person gives explicit permission via a simple public page fetch. This sidesteps most ToS risk and still teaches you the same concepts
- Write `scraper/profile_scraper.py` and `scraper/parser.py`
- Milestone: Given a block of profile text, parser extracts name, headline, and any recent activity into a `ScrapedProfile` Pydantic object

### **Day 3 — Rate Limiting + Ethical Guardrails**
**Goal:** Responsible design baked in from the start, not bolted on later.

- Write `scraper/rate_limiter.py` — even if using pasted text for MVP, build this properly as if scraping live, since it shows engineering maturity
- Write `docs/ethical_use.md` — document your reasoning now, while it's fresh
- Add input validation: reject clearly malicious inputs, add basic length limits
- Milestone: You can explain in 2 sentences why you made each ethical design choice

### **Day 4 — Prompt Engineering**
**Goal:** The prompts that turn profile data into a genuinely good message.

- Write `agent/prompts.py` — system prompt + few-shot examples of GOOD outreach (specific, references real details) vs BAD outreach (generic, spammy)
- Write `generator/tone_templates.py` — formal, casual, technical variations
- Test prompts directly against an LLM (no agent wrapper yet) with 3-4 sample profiles
- Milestone: You can generate a message manually (not yet through your agent code) that references a specific real detail and doesn't sound like spam

### **Day 5 — Agent + Tool Calling**
**Goal:** Wrap the scraper and generator as tools the agent orchestrates.

- Write `agent/tools.py` — define `scrape_profile` and `generate_message` as callable tools
- Write `agent/agent_core.py` — agent logic that calls scraper first, passes result to generator
- This is your core "AI Agent" concept from the course — use function/tool calling properly here
- Milestone: Agent takes raw input, calls both tools in sequence, returns a message — all through code, no manual steps

### **Day 6 — Message Builder + Output Validation**
**Goal:** Structured, validated output every time.

- Write `generator/message_builder.py` — constructs the final prompt combining profile + product info + tone
- Wire up `response_models.py` validation on every agent output
- Add the `reason_for_outreach` field — a one-line explanation of WHY this message fits this person (useful for the user reviewing it)
- Milestone: 10 test profiles run through the full pipeline, all produce valid, distinct, non-generic messages

### **Day 7 — CSV Export + Batch Processing**
**Goal:** Handle multiple profiles at once, output usable CSV.

- Write `export/csv_exporter.py`
- Add `BatchRequest`/`BatchResponse` models for processing a list of profiles in one call
- Add basic error handling — if one profile in a batch fails, others still complete
- Milestone: Feed in 5 profiles, get back one clean CSV with all 5 messages, no crashes on a bad entry

### **Day 8 — FastAPI Wiring**
**Goal:** A real, usable API.

- Write `api/routes.py` — `/generate` (single) and `/generate-batch` (multiple) endpoints
- Add basic error responses (400 for bad input, 500 handled gracefully)
- Write `main.py` to tie it all together
- Milestone: Hit both endpoints via Postman/curl, get correct responses and proper error handling on bad input

### **Day 9 — Testing + Polish**
**Goal:** Confidence the thing actually works, and it looks clean.

- Write basic tests in `tests/` — at minimum, test Pydantic models reject bad input, test the message builder produces non-empty output
- Clean up code — consistent naming, remove dead code, add docstrings to key functions
- Write `docs/architecture.md` with the diagram from section 4
- Milestone: Someone else could clone your repo and understand what each folder does within 2 minutes

### **Day 10 — README, Demo, Real Users**
**Goal:** Ship it and get real feedback.

- Finalize `README.md` (template above)
- Record a 2-minute demo video — show input, show output, explain the ethical design choice
- Share with 3-5 real people (freelancer friends, founder acquaintances, LinkedIn) — get actual usage
- Push to GitHub with clean commit history
- Milestone: At least 1 real person outside yourself has used it and given feedback

---

## 7. THINGS TO EXPLICITLY AVOID (SCOPE CREEP TRAPS)

- **Do not build a frontend.** API + CSV output is enough. A UI is a distraction from your actual goal and timeline.
- **Do not attempt live LinkedIn scraping with login/session handling.** This is a legal gray area and a technical rabbit hole. Pasted profile text or public page fetch only.
- **Do not add a database.** Stateless request → response is enough for this project. No need for user accounts, history storage, etc.
- **Do not add authentication.** Not needed for this specific project's scope — you already get auth concept exposure from your web dev block.
- **Do not try to support multiple LLM providers on day 1.** Pick one (OpenAI or Gemini), get it fully working, add provider-switching only if time remains at the very end.

---

## 8. WHAT TO GIVE CLAUDE FOR PLANNING SESSIONS

When you come back for each day's build, give Claude:
1. This full document (paste directly)
2. Which day you're on
3. Any code you've already written for context
4. Specific blockers if you have any

This keeps every planning conversation grounded in the same structure without re-explaining the project each time.

---

## 9. INTERVIEW EXPLANATION (prepare this by Day 10)

*"I built OutreachIQ, an AI agent that generates personalized LinkedIn outreach messages. It uses tool calling — the agent first calls a tool that extracts public profile information, then passes that to a second tool that generates a message using prompt engineering with few-shot examples of good vs spammy outreach. Every input and output is validated with Pydantic models. I deliberately did not automate sending messages or scrape private data — the tool generates drafts a human reviews and sends manually, which respects LinkedIn's terms of service. It outputs a CSV so users can batch-process multiple profiles at once. I got 3-5 real freelancers to test it and used their feedback to improve the tone templates."*
