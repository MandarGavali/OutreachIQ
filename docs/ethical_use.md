# Ethical Use of OutreachIQ

## Purpose

OutreachIQ is designed to help users create personalized LinkedIn outreach message drafts using publicly available profile information. The project focuses on improving message quality while encouraging responsible and ethical use.

---

## Design Principles

### 1. Human-in-the-Loop

OutreachIQ only generates message drafts.

Users must manually review, edit, and send every message.

The system never sends messages automatically.

---

### 2. User-Provided Data Only

The application relies entirely on user-provided profile data (pasted text or uploaded PDFs) and does NOT perform unauthorized scraping of LinkedIn or circumvent platform access controls.

Users are responsible for ensuring they have the right to process the profile data they provide.

---

### 3. No Mass Automation

The project is intentionally not designed for spam campaigns or bulk messaging.

Its goal is to improve thoughtful one-to-one communication.

---

### 4. Responsible Resource Usage

If external profile fetching is added in the future, requests should be rate-limited to avoid excessive traffic and to respect service providers.

---

### 5. Transparency

Generated messages are AI-assisted drafts.

Users are responsible for reviewing content before sending it.

---

## Future Improvements

- Better input validation
- Configurable rate limits
- Support for additional public data sources
- Improved monitoring and logging