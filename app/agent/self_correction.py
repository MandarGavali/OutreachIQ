"""
Self-correction orchestration for OutreachIQ Phase 3.

Responsibilities:
  - Generate an initial outreach message
  - Evaluate the message using the evaluator
  - If the score is below the threshold, regenerate using evaluator feedback
  - Track all attempts and always return the highest-scoring valid message
  - Enforce the maximum attempt limit (never loop infinitely)

Architecture decision:
  Self-correction runs inside the generate_message tool (an internal service).
  The Phase 2 OutreachAgent custom loop is unchanged.
  The LLM calls generate_message; the tool internally orchestrates the loop.

Python controls:
  - attempt count
  - threshold comparison
  - best-message selection
  - stopping conditions

The LLM provides:
  - generated message content
  - evaluation scores and feedback

This separation is intentional: the LLM cannot short-circuit the loop.
"""

from __future__ import annotations

import logging

from pydantic import ValidationError

from app.config import settings
from app.generator.message_builder import build_prompt, build_regeneration_prompt
from app.models.evaluation_models import (
    AttemptRecord,
    EvaluationResult,
    SelfCorrectionResult,
)
from app.models.profile_models import ScrapedProfile
from app.models.request_models import Tone
from app.models.response_models import OutreachMessage

logger = logging.getLogger(__name__)


def run_self_correction(
    profile: ScrapedProfile,
    product_description: str,
    tone: Tone,
    generate_fn,
    evaluate_fn,
    max_attempts: int | None = None,
    threshold: float | None = None,
    enabled: bool | None = None,
) -> SelfCorrectionResult:
    """
    Run the generate → evaluate → (optionally) regenerate loop.

    Args:
        profile: ScrapedProfile to personalize for.
        product_description: Product/service description.
        tone: Desired tone.
        generate_fn: Callable(prompt: str) → OutreachMessage.
                     Accepts the generator function as a dependency so tests
                     can inject a fake without monkeypatching globals.
        evaluate_fn: Callable(profile, message, product_description, tone)
                     → EvaluationResult.
        max_attempts: Override for MAX_SELF_CORRECTION_ATTEMPTS.
        threshold: Override for SELF_CORRECTION_SCORE_THRESHOLD.
        enabled: Override for SELF_CORRECTION_ENABLED feature flag.

    Returns:
        SelfCorrectionResult with the best message, its evaluation, and history.
    """
    _max = max_attempts if max_attempts is not None else settings.MAX_SELF_CORRECTION_ATTEMPTS
    _threshold = threshold if threshold is not None else settings.SELF_CORRECTION_SCORE_THRESHOLD
    _enabled = enabled if enabled is not None else settings.SELF_CORRECTION_ENABLED

    logger.info(
        "[SelfCorrection] Started — enabled=%s max_attempts=%d threshold=%.1f",
        _enabled,
        _max,
        _threshold,
    )

    history: list[AttemptRecord] = []
    best_message: OutreachMessage | None = None
    best_evaluation: EvaluationResult | None = None

    # --- Feature flag: skip evaluation ---
    if not _enabled:
        logger.info("[SelfCorrection] Feature disabled — generating once without evaluation")
        initial_prompt = build_prompt(
            profile=profile,
            product_description=product_description,
            tone=tone,
        )
        message = generate_fn(initial_prompt)
        # Return a minimal result without evaluation
        dummy_eval = _make_skipped_evaluation()
        return SelfCorrectionResult(
            final_message=message,
            final_evaluation=dummy_eval,
            attempt_count=1,
            improved=False,
            history=[AttemptRecord(attempt=1, message=message, evaluation=dummy_eval)],
        )

    for attempt_num in range(1, _max + 1):
        logger.info("[SelfCorrection] Attempt %d / %d", attempt_num, _max)

        # --- Build the appropriate prompt ---
        if attempt_num == 1:
            prompt = build_prompt(
                profile=profile,
                product_description=product_description,
                tone=tone,
            )
        else:
            # Regeneration: pass previous message + evaluation feedback
            assert best_message is not None
            assert best_evaluation is not None
            prompt = build_regeneration_prompt(
                profile=profile,
                product_description=product_description,
                tone=tone,
                previous_message=best_message,
                evaluation=best_evaluation,
            )

        # --- Generate ---
        logger.info("[SelfCorrection] Generating message (attempt %d)", attempt_num)
        try:
            message = generate_fn(prompt)
        except Exception as exc:
            logger.warning(
                "[SelfCorrection] Generation failed on attempt %d: %s",
                attempt_num,
                type(exc).__name__,
            )
            if best_message is not None:
                # Use best valid message from a prior attempt
                logger.info("[SelfCorrection] Returning best previous message")
                break
            raise  # No valid message at all — propagate

        # --- Evaluate ---
        logger.info("[SelfCorrection] Evaluating message (attempt %d)", attempt_num)
        try:
            evaluation = evaluate_fn(profile, message, product_description, tone)
        except Exception as exc:
            logger.warning(
                "[SelfCorrection] Evaluation failed on attempt %d: %s",
                attempt_num,
                type(exc).__name__,
            )
            # Evaluation failure — record the message with a failure evaluation
            fail_eval = _make_failure_evaluation(str(exc))
            history.append(AttemptRecord(attempt=attempt_num, message=message, evaluation=fail_eval))
            # Keep the message if it's our only option
            if best_message is None:
                best_message = message
                best_evaluation = fail_eval
            break

        # --- Track attempt ---
        history.append(AttemptRecord(attempt=attempt_num, message=message, evaluation=evaluation))
        logger.info(
            "[SelfCorrection] Attempt %d score=%.2f passed=%s",
            attempt_num,
            evaluation.overall_score,
            evaluation.passed,
        )

        # --- Update best ---
        if best_evaluation is None or evaluation.overall_score > best_evaluation.overall_score:
            logger.info(
                "[SelfCorrection] New best: %.2f (was %.2f)",
                evaluation.overall_score,
                best_evaluation.overall_score if best_evaluation else 0.0,
            )
            best_message = message
            best_evaluation = evaluation

        # --- Stop if quality is sufficient ---
        if evaluation.passed:
            logger.info(
                "[SelfCorrection] Quality threshold met on attempt %d (%.2f >= %.1f)",
                attempt_num,
                evaluation.overall_score,
                _threshold,
            )
            break

        # --- Last attempt exhausted ---
        if attempt_num == _max:
            logger.info(
                "[SelfCorrection] Max attempts reached. Best score: %.2f",
                best_evaluation.overall_score if best_evaluation else 0.0,
            )

    assert best_message is not None
    assert best_evaluation is not None

    first_score = history[0].evaluation.overall_score if history else 0.0
    final_score = best_evaluation.overall_score
    improved = final_score > first_score

    logger.info(
        "[SelfCorrection] Complete — attempts=%d initial_score=%.2f final_score=%.2f improved=%s",
        len(history),
        first_score,
        final_score,
        improved,
    )

    return SelfCorrectionResult(
        final_message=best_message,
        final_evaluation=best_evaluation,
        attempt_count=len(history),
        improved=improved,
        history=history,
    )


# ---------------------------------------------------------------------------
# Helpers for failed / skipped evaluations
# ---------------------------------------------------------------------------

def _make_skipped_evaluation() -> EvaluationResult:
    """
    Produce a placeholder EvaluationResult when self-correction is disabled.

    Scores are all 0.0 so the evaluator is clearly marked as skipped.
    The model_validator will still compute overall_score = 0.0 and set
    passed according to the threshold.
    """
    return EvaluationResult(
        personalization=0.0,
        relevance=0.0,
        specificity=0.0,
        naturalness=0.0,
        non_spamminess=0.0,
        factuality=0.0,
        feedback="Self-correction disabled; message was not evaluated.",
        improvement_suggestions=[],
        evidence_used=[],
        passed=False,  # overridden by model_validator
    )


def _make_failure_evaluation(error_message: str) -> EvaluationResult:
    """
    Produce a placeholder EvaluationResult when the evaluator LLM call fails.
    """
    return EvaluationResult(
        personalization=0.0,
        relevance=0.0,
        specificity=0.0,
        naturalness=0.0,
        non_spamminess=0.0,
        factuality=0.0,
        feedback=f"Evaluation unavailable: {error_message[:200]}",
        improvement_suggestions=[],
        evidence_used=[],
        passed=False,  # overridden by model_validator
    )
