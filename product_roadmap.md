# OutreachIQ → Full LinkedIn Outreach SaaS
### Product Roadmap: From V1 to Prosp-Level Platform

> **Starting point**: You have a working AI personalization engine (OutreachIQ V1) with FastAPI, LangChain agent, Pydantic validation, profile parsing, tone control, batch processing, CSV export, and full test coverage.
> **Target**: A cloud-executed, multi-account LinkedIn outreach SaaS with AI personalization, voice notes, campaign sequences, lead discovery, and a unified inbox.

---

## What Prosp Actually Is (After Research)

Prosp is a **cloud-based LinkedIn outreach automation platform** priced per connected LinkedIn account ($19–$80/account/month depending on volume and billing cycle). Every plan includes:

- **Free dedicated residential proxy** per account
- **Unlimited AI message writing** from prospect profile + social activity data
- **Unlimited AI reply assistance**
- **Automated personalized voice notes** with **voice cloning**
- **Built-in Lead Finder** + Chrome extension for extracting leads
- **Visual campaign sequence builder** with reply-detection branching
- **Unified inbox** across all connected accounts
- **Multi-account rotation** for agency use
- **Cloud execution 24/7** (no computer required)

Their key differentiator over competitors (Expandi, HeyReach): unlimited AI + native voice notes + all features included at a lower per-account price.

---

## The Engineering Gap

```text
WHAT YOU HAVE                          WHAT YOU NEED TO ADD
─────────────────────────────          ───────────────────────────────────────
✅ AI personalization engine           ❌ Lead discovery & enrichment
✅ LangChain agent + tool calling      ❌ LinkedIn session management
✅ Pydantic models + validation        ❌ Campaign sequence engine (state machine)
✅ FastAPI REST API                    ❌ Background job workers (Celery/Redis)
✅ Batch processing                    ❌ LinkedIn action execution (browser)
✅ CSV export                          ❌ Voice cloning + AI voice note generation
✅ Profile parser                      ❌ Unified inbox aggregation
✅ Test suite (pytest)                 ❌ React/Next.js frontend
                                       ❌ Auth, subscriptions, multi-tenancy
                                       ❌ PostgreSQL, Redis, Stripe
                                       ❌ Proxy management
                                       ❌ Rate limiting + anti-abuse
```

---

## V2 — Lead Intelligence Layer

> **"Who should I contact?"**
> Build the system that answers this question before message generation even starts.

### What you'll build
- **Lead database** with PostgreSQL (store prospect profiles with ICP metadata)
- **Lead Finder UI/API** — search by job title, company, industry, location
- **Lead import** — CSV upload, manual entry
- **ICP (Ideal Customer Profile) definition** — define who you're targeting
- **Lead scoring** — rank leads against your ICP automatically
- **Deduplication** — detect and prevent duplicate contacts
- **Enrichment** — augment leads with additional data (company size, industry)

### New Tech Stack Additions
| Technology | Purpose |
|---|---|
| **PostgreSQL** | Persistent lead database |
| **SQLAlchemy** | ORM for Python |
| **Alembic** | Database migrations |
| **Pydantic v2** | Extended data models for leads |

### Key Learning Outcomes
- Relational database design
- SQL queries and indexing
- Data modeling for business entities
- Database migrations

### What to build first
```text
1. Lead model (PostgreSQL schema)
2. CRUD API endpoints for leads (/leads)
3. CSV import endpoint
4. Basic filtering/search API
5. ICP model + scoring logic
6. Deduplication logic
```

---

## V3 — Campaign Engine

> **"What should happen after I find them?"**
> Build a workflow engine that chains LinkedIn actions in a sequence.

### The Core Problem
You need to model this as a **state machine**:

```text
Lead enters campaign
        │
        ▼
[PENDING] → Visit profile
        │
        ▼
[VISITED] → Wait 2 days
        │
        ▼
[WAIT_CONNECTION] → Send connection request
        │
        ▼
[CONNECTION_SENT] → Wait for acceptance
        │                    │
        ▼                    ▼
[CONNECTED]          [TIMEOUT → skip to next]
        │
        ▼
[MESSAGE_PENDING] → AI personalized message (your V1!)
        │
        ▼
[MESSAGE_SENT] → Wait 3 days
        │
        ▼
[FOLLOW_UP_PENDING] → Follow-up message
        │
        ▼
[REPLIED] → STOP (remove from sequence)
[NO_REPLY] → Mark as cold
```

### New Tech Stack Additions
| Technology | Purpose |
|---|---|
| **Redis** | Task queue broker |
| **Celery** | Async task workers |
| **Celery Beat** | Scheduled task execution |
| **PostgreSQL** | Campaign state persistence |

### Key Learning Outcomes
- State machine design
- Message queues and async workers
- Job scheduling and retries
- Event-driven architecture
- Concurrency control

### What to build
```text
1. Campaign model (name, steps, status)
2. CampaignStep model (action type, delay, conditions)
3. LeadCampaignEnrollment model (current state per lead)
4. Celery workers that poll and execute next steps
5. State transition logic with guard conditions
6. Reply detection (pauses sequence)
7. Campaign analytics (sent/replied/accepted rates)
```

### Campaign Data Model
```python
class CampaignStep(BaseModel):
    step_type: Literal["visit_profile", "connection_request", 
                        "send_message", "follow_up", "wait"]
    delay_days: int
    conditions: dict  # e.g., {"require_connection": True}
    ai_personalize: bool

class Campaign(BaseModel):
    name: str
    steps: list[CampaignStep]
    status: Literal["draft", "active", "paused", "completed"]
```

---

## V4 — LinkedIn Integration (The Hard Part)

> **"Actually execute the actions on LinkedIn."**

### The Core Problem
You need to control a real LinkedIn session and perform actions on behalf of a user. This is the most technically complex component.

### Two Approaches

**Option A — Browser Automation (Playwright/Puppeteer)**
- Control a real Chrome/Chromium browser with a user's LinkedIn session
- Simulate human actions: scroll, click, type, wait
- Inject residential proxy per account
- Run headless in the cloud

**Option B — LinkedIn API (limited)**
- LinkedIn has a Partner API but it's heavily restricted
- Not practical for automation use case at this stage

### You'll need to build
```text
1. LinkedIn Session Manager
   - Store session cookies securely (encrypted)
   - Browser pool management (one Playwright instance per account)
   - Session health checks (detect if logged out)

2. Action Executor
   - visit_profile(profile_url)
   - send_connection_request(profile_url, message?)
   - send_message(conversation_id, message_text)
   - send_voice_note(conversation_id, audio_file)
   - check_connection_status(profile_url)
   - get_new_messages()

3. Rate Limiter (Critical for safety)
   - Max ~100 connection requests/week
   - Max ~80 messages/day
   - Randomized delays between actions (human pacing)
   - Daily/weekly quota tracking per account

4. Proxy Manager
   - Assign one residential proxy per LinkedIn account
   - Rotate on request failure
   - Health check proxies

5. Error Recovery
   - Detect LinkedIn CAPTCHA
   - Detect account restrictions
   - Retry logic with exponential backoff
   - Alert user on account health issues
```

### New Tech Stack Additions
| Technology | Purpose |
|---|---|
| **Playwright** | Browser automation |
| **Playwright-Stealth** | Anti-detection (human-like behavior) |
| **Redis** | Session state caching |
| **Cryptography (Fernet)** | Encrypt stored session tokens |

### Key Learning Outcomes
- Browser automation at scale
- Session management and security
- Proxy infrastructure
- Concurrency and resource management
- Failure recovery and circuit breakers

> [!CAUTION]
> This stage requires careful study of LinkedIn's Terms of Service. Prosp operates in this space commercially, but you need to design your system with rate limiting and anti-abuse measures as core constraints, not afterthoughts.

---

## V5 — Voice AI

> **"Make outreach sound human."**

### What you'll build
- **Voice Cloning** — user records 30s sample → model clones their voice
- **Script Generation** — AI generates personalized voice note script per prospect
- **Audio Generation** — TTS with cloned voice
- **Audio Delivery** — attach to LinkedIn message as voice note

### How Prosp does it
Clone once → generate at scale with AI-written scripts personalized per prospect based on their profile data.

### APIs to use
| Service | Purpose | Pricing |
|---|---|---|
| **ElevenLabs** | Voice cloning + TTS | Pay-per-character |
| **OpenAI TTS** | Simpler TTS (no cloning) | Pay-per-character |
| **Cartesia** | Newer, faster, cheaper option | Pay-per-second |

### What to build
```text
1. VoiceProfile model (user's cloned voice ID)
2. Voice cloning endpoint (upload sample → get voice_id)
3. Script generation tool (AI writes 15-20s script from prospect data)
4. Audio generation (ElevenLabs API → .mp3 file)
5. Store audio in cloud storage (S3/R2)
6. Attach audio to LinkedIn voice note action in campaign engine
```

### New Tech Stack Additions
| Technology | Purpose |
|---|---|
| **ElevenLabs SDK** | Voice cloning + TTS |
| **AWS S3 / Cloudflare R2** | Audio file storage |
| **FFmpeg** | Audio processing/compression |

### Key Learning Outcomes
- AI audio APIs
- File storage and CDN delivery
- Async media processing pipelines

---

## V6 — Unified Inbox

> **"Manage all the conversations."**

### What you'll build
```text
LinkedIn Account A ──┐
LinkedIn Account B ──┼──→ Message Aggregator → Unified Inbox DB
LinkedIn Account C ──┘                               │
                                                     ▼
                                              Frontend Inbox UI
                                                     │
                                         ┌───────────┼───────────┐
                                         ▼           ▼           ▼
                                      Replies    Lead Status   Tags
```

### Features
- Poll all connected LinkedIn accounts for new messages on a schedule
- Normalize messages into unified inbox schema
- Tag conversations (hot, cold, replied, needs follow-up)
- Reply from unified inbox (routes back through correct account)
- AI reply suggestions
- Reminders and snooze

### What to build
```text
1. Message polling workers (Celery periodic tasks per account)
2. Unified message schema + PostgreSQL storage
3. Inbox API endpoints (GET /inbox, POST /inbox/:id/reply)
4. WebSocket for real-time inbox updates
5. Conversation threading logic
6. Tag and status management
```

### New Tech Stack Additions
| Technology | Purpose |
|---|---|
| **WebSockets (FastAPI)** | Real-time inbox updates |
| **Background scheduler** | Periodic message polling |

---

## V7 — Full SaaS Platform

> **"Turn it into an actual product."**

### Frontend
- **Next.js 14** (App Router) — full-stack React framework
- **TypeScript** — type safety
- **Tailwind CSS** — styling
- **shadcn/ui** — component library
- **Recharts / Tremor** — analytics charts

### Authentication
- **Clerk** or **Auth.js** — user authentication
- Email + Google OAuth
- Organization/workspace model (one org → many LinkedIn accounts)
- RBAC: Owner / Admin / Member roles

### Payments
- **Stripe** — subscription billing
- Pricing: per connected LinkedIn account (mirror Prosp's model)
- Usage-based billing (track actions per account per billing period)
- Trial period (no credit card required for first 7 days)

### Infrastructure
| Component | Technology |
|---|---|
| **Database** | PostgreSQL (Supabase or Railway) |
| **Cache + Queue Broker** | Redis (Upstash) |
| **Background Workers** | Celery (deployed on Railway/Fly.io) |
| **Browser Automation** | Playwright (Docker containers) |
| **File Storage** | Cloudflare R2 |
| **API Backend** | FastAPI (your existing codebase) |
| **Frontend** | Next.js on Vercel |
| **Observability** | Sentry + PostHog |
| **Email** | Resend |

### Multi-tenancy Model
```text
Organization
    │
    ├── Users (with roles)
    │
    ├── LinkedIn Accounts (connected)
    │       └── Proxy (1:1 per account)
    │
    ├── Leads (scoped to org)
    │
    └── Campaigns
            └── Campaign Enrollments (per lead per account)
```

### Subscription Model (mirroring Prosp)
```text
Per LinkedIn account per month:
  1-5 accounts:   $79.99/account/mo (monthly)
  6-30 accounts:  $59.99/account/mo
  31+ accounts:   $39.99/account/mo
Annual discount: ~23% off
```

---

## Overall Timeline Estimate

| Version | What you build | Estimated Duration |
|---|---|---|
| **V1** ✅ | AI Outreach Engine | DONE |
| **V2** | Lead Intelligence | 2–3 weeks |
| **V3** | Campaign Engine | 3–4 weeks |
| **V4** | LinkedIn Integration | 4–6 weeks |
| **V5** | Voice AI | 1–2 weeks |
| **V6** | Unified Inbox | 2–3 weeks |
| **V7** | Full SaaS Platform | 4–6 weeks |

**Total: ~4-6 months of focused building**

---

## Skills You'll Learn at Each Stage

```text
V2: PostgreSQL, SQLAlchemy, Alembic, data modeling
V3: State machines, Celery, Redis, async workers, scheduling
V4: Playwright, browser automation, proxy management, 
    rate limiting, session security, failure recovery
V5: AI audio APIs, file storage, media pipelines
V6: WebSockets, real-time systems, message aggregation
V7: Next.js, TypeScript, Stripe, multi-tenancy, 
    RBAC, observability, cloud deployment
```

---

## What to Build Next (V2 — Immediate Next Steps)

1. **Set up PostgreSQL** — install locally with Docker
2. **Design the Lead schema** — name, headline, company, profile_url, icp_score, created_at
3. **Add SQLAlchemy to your FastAPI app**
4. **Create lead CRUD endpoints** — POST /leads, GET /leads, GET /leads/:id, DELETE /leads/:id
5. **Build CSV import** — extend your existing CSV exporter to also import leads
6. **Add simple filtering** — filter by company, title, industry via query params
7. **Define ICP model** — what job titles, industries, company sizes you're targeting
8. **Build lead scoring** — score each lead against your ICP definition

> **Start here**: `docker run -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:16`

---

## Key Architecture Principle

Every version builds directly on the previous one:

```text
OutreachIQ V1 (your AI engine)
         │
         ▼
V2 adds: lead database underneath
         │
         ▼
V3 adds: campaign engine on top, feeds leads into sequences
         │
         ▼
V4 adds: LinkedIn executor underneath the campaign engine
         │
         ▼
V5 adds: voice generation as a new step type in the campaign engine
         │
         ▼
V6 adds: inbox aggregator that reads from the LinkedIn executor
         │
         ▼
V7 wraps: entire system in a SaaS shell with auth + billing + frontend
```

**You are not rewriting. You are layering.**

That's the correct mental model for building this incrementally.
