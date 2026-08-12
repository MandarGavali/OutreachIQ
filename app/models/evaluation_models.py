"""
Pydantic models for the Phase 3 self-correction evaluation system.

EvaluationResult
    Structured quality assessment returned by the evaluator LLM call.
    All component scores are bounded 0–10.
    overall_score is computed by Python (not trusted from the LLM).

SelfCorrectionResult
    Internal result of the full self-correction loop.
    Contains the best OutreachMessage, its evaluation, attempt count,
    and the complete attempt history for debugging / Phase 4 analytics.

Score semantics (all dimensions 0–10, higher = better):
    personalization  — how well the message is tailored to this specific person
    relevance        — how well the product/service connects to the profile
    specificity      — how concrete and grounded in profile facts the message is
    naturalness      — how human-sounding vs. templated/automated the message feels
    non_spamminess   — inverse of sales pressure; 10 = respectful, 0 = aggressive spam
    factuality       — degree to which claims are supported by the supplied profile

overall_score is a weighted average (weights documented below).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.response_models import OutreachMessage

# ---------------------------------------------------------------------------
# Score weights — must sum to 1.0
# ---------------------------------------------------------------------------
#
# Personalization  0.25  — core differentiator; most important single dimension
# Relevance        0.20  — product–profile fit matters for conversion
# Specificity      0.20  — specificity is evidence of personalization quality
# Factuality       0.20  — fabricated claims cause trust damage; must not be rewarded
# Naturalness      0.10  — tone matters but is less critical than grounding
# Non-spamminess   0.05  — binary-ish; low-pressure messages are table stakes
#
_WEIGHTS = {
    "personalization": 0.25,
    "relevance": 0.20,
    "specificity": 0.20,
    "factuality": 0.20,
    "naturalness": 0.10,
    "non_spamminess": 0.05,
}
assert abs(sum(_WEIGHTS.values()) - 1.0) < 1e-9, "Score weights must sum to 1.0"


def _bounded_score(name: str) -> Any:
    """Return a Pydantic Field for a 0–10 bounded score."""
    return Field(
        ...,
        ge=0.0,
        le=10.0,
        description=f"{name} score (0 = poor, 10 = excellent).",
    )


class EvaluationResult(BaseModel):
    """
    Structured quality assessment of a generated outreach message.

    Returned by the evaluator component.  Python computes overall_score
    from the component scores using _WEIGHTS so we do not rely on the
    LLM to perform arithmetic correctly.
    """

    # --- Component scores (LLM-populated) ---
    personalization: float = _bounded_score("Personalization")
    relevance: float = _bounded_score("Relevance")
    specificity: float = _bounded_score("Specificity")
    naturalness: float = _bounded_score("Naturalness")
    non_spamminess: float = _bounded_score("Non-spamminess")
    factuality: float = _bounded_score("Factuality")

    # --- Qualitative fields ---
    feedback: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description=(
            "Actionable feedback explaining the scores and what should be "
            "improved in the next generation attempt."
        ),
    )
    improvement_suggestions: list[str] = Field(
        default_factory=list,
        description="Specific, actionable suggestions for the next generation attempt.",
    )
    evidence_used: list[str] = Field(
        default_factory=list,
        description=(
            "Profile evidence that was actually referenced by the message "
            "(e.g., 'headline mentions AI agents'). Empty if no grounding found."
        ),
    )
    passed: bool = Field(
        ...,
        description=(
            "Whether the message meets the quality threshold.  "
            "Set by Python after computing overall_score; "
            "the LLM field is overridden by the validator."
        ),
    )

    # --- Python-computed overall score ---
    overall_score: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="Weighted overall quality score computed by Python.",
    )

    @model_validator(mode="after")
    def _compute_overall_and_pass(self) -> "EvaluationResult":
        """
        Compute overall_score from component scores using _WEIGHTS and
        override the LLM-supplied 'passed' boolean so Python controls
        the pass/fail decision.
        """
        raw = (
            self.personalization * _WEIGHTS["personalization"]
            + self.relevance * _WEIGHTS["relevance"]
            + self.specificity * _WEIGHTS["specificity"]
            + self.factuality * _WEIGHTS["factuality"]
            + self.naturalness * _WEIGHTS["naturalness"]
            + self.non_spamminess * _WEIGHTS["non_spamminess"]
        )
        self.overall_score = round(raw, 2)
        # 'passed' is deliberately overwritten here; the LLM value is ignored
        # to prevent the model from self-approving a weak message.
        from app.config import settings
        self.passed = self.overall_score >= settings.SELF_CORRECTION_SCORE_THRESHOLD
        return self


class AttemptRecord(BaseModel):
    """Record of a single generation + evaluation attempt."""

    attempt: int = Field(..., ge=1, description="1-based attempt number.")
    message: OutreachMessage
    evaluation: EvaluationResult


class SelfCorrectionResult(BaseModel):
    """
    Output of the full self-correction loop.

    The public API surface (routes.py) continues to return OutreachMessage.
    SelfCorrectionResult is used internally by the generate_message tool
    and can be exposed in Phase 4 for analytics.
    """

    final_message: OutreachMessage
    final_evaluation: EvaluationResult
    attempt_count: int = Field(..., ge=1)
    improved: bool = Field(
        description="True if a later attempt scored higher than the first."
    )
    history: list[AttemptRecord] = Field(
        default_factory=list,
        description="Full attempt history for debugging and analytics.",
    )
