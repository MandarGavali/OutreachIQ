# OutreachIQ V2 — Self-Correction Personalization

## Why Self-Correction Exists

In V1, OutreachIQ generated an outreach message and immediately returned it to the user. While often good, the LLM occasionally produced generic statements, missed key personalization opportunities, or hallucinated facts not present in the profile.

Phase 3 introduces a **Self-Correction Quality Gate**. Before a message is returned, a separate Evaluator grades the message. If the message falls below a configured quality threshold, the system provides structured feedback to the generator and forces a regeneration. This guarantees that weak messages are automatically improved before a human ever sees them.

## The Self-Correction Loop

```text
Generate Initial Message
         │
         ▼
Evaluate Message (Evaluator)
         │
         ├── PASS (Score >= Threshold) ───────► Return Message
         │
         ▼
        FAIL
         │
         ▼
Build Regeneration Prompt (with feedback)
         │
         ▼
Regenerate Message
         │
         ▼
Evaluate Regenerated Message
         │
         ▼
Select and Return Highest-Scoring Valid Message
```

## Evaluator Responsibilities

The Evaluator is a strictly separated component (`app.agent.evaluator`).
- **Input:** Profile data, product description, tone, and the *generated message*.
- **Output:** A structured `EvaluationResult` containing component scores and feedback.

**Security:** The Evaluator treats the profile entirely as **UNTRUSTED EXTERNAL DATA**. The evaluator prompt explicitly wraps profile fields in `DATA` blocks and instructs the LLM never to follow instructions embedded within them.

## Evaluation Dimensions

The message is scored across six dimensions (0–10 scale). The weights are used by Python to compute the `overall_score`.

| Dimension | Weight | Description |
|---|---|---|
| **Personalization** | 25% | Is the message tailored to this specific person? |
| **Relevance** | 20% | Does the product logically connect to the profile? |
| **Specificity** | 20% | Does the message use concrete details instead of generic platitudes? |
| **Factuality** | 20% | Are the claims supported by the supplied profile? (Fabrications score low). |
| **Naturalness** | 10% | Does the message sound like a human wrote it? |
| **Non-spamminess**| 5% | Is the message respectful and low-pressure? |

## Threshold and Retry Limit

The self-correction orchestrator is controlled entirely by Python logic (not the LLM) to prevent infinite loops and ensure deterministic behavior.

- `SELF_CORRECTION_SCORE_THRESHOLD = 7.0` (Configurable in `app/config.py`)
- `MAX_SELF_CORRECTION_ATTEMPTS = 2`

**Best-Message Selection:** If regeneration occurs but the second message scores *lower* than the first message, the system returns the **first** message. The system always returns the highest-scoring valid attempt.

## Architecture Integration

Self-correction is implemented as an internal service behind the `generate_message` tool.

The Phase 2 custom agent loop (`OutreachAgent`) is entirely unchanged. The LLM simply calls `generate_message`. Inside that tool, the self-correction service takes over, orchestrates the generate → evaluate → regenerate loop, and returns the final best result to the agent.

## Error Handling

- If the Evaluator fails (API error or malformed JSON), the system falls back gracefully and returns the best generated message without a score.
- If Generation fails during attempt 2, the system returns attempt 1.
- If all attempts fail the threshold, the highest-scoring attempt is returned.
- A feature flag (`SELF_CORRECTION_ENABLED`) allows disabling the evaluator entirely, reverting to single-generation behavior without breaking the architecture.
