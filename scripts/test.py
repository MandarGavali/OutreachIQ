import pytest
from pydantic import ValidationError

from app.models.request_models import (
    Tone,
    OutreachRequest,
    BatchRequest,
)
from app.models.response_models import (
    OutreachMessage,
    BatchResponse,
)


# -------------------------
# OutreachRequest
# -------------------------

def test_valid_outreach_request():
    request = OutreachRequest(
        profile_url="https://linkedin.com/in/johndoe",
        product_description="AI-powered recruitment automation platform",
        tone=Tone.CASUAL,
    )

    assert request.profile_url == "https://linkedin.com/in/johndoe"
    assert request.tone == Tone.CASUAL


def test_short_product_description_rejected():
    with pytest.raises(ValidationError):
        OutreachRequest(
            profile_url="https://linkedin.com/in/johndoe",
            product_description="Too short",
        )


def test_long_product_description_rejected():
    with pytest.raises(ValidationError):
        OutreachRequest(
            profile_url="https://linkedin.com/in/johndoe",
            product_description="A" * 1001,
        )


def test_default_tone_is_casual():
    request = OutreachRequest(
        profile_url="https://linkedin.com/in/johndoe",
        product_description="AI-powered recruitment automation platform",
    )

    assert request.tone == Tone.CASUAL


def test_invalid_tone_rejected():
    with pytest.raises(ValidationError):
        OutreachRequest(
            profile_url="https://linkedin.com/in/johndoe",
            product_description="AI-powered recruitment automation platform",
            tone="random",
        )


# -------------------------
# BatchRequest
# -------------------------

def test_valid_batch_request():
    request = OutreachRequest(
        profile_url="https://linkedin.com/in/johndoe",
        product_description="AI-powered recruitment automation platform",
    )

    batch = BatchRequest(requests=[request])

    assert len(batch.requests) == 1


def test_empty_batch_rejected():
    with pytest.raises(ValidationError):
        BatchRequest(requests=[])


# -------------------------
# OutreachMessage
# -------------------------

def test_valid_outreach_message():
    message = OutreachMessage(
        recipient_name="John Doe",
        message=(
            "I noticed your recent work in AI recruitment and thought "
            "our platform could be relevant to the problems you're solving."
        ),
        reason_for_outreach="Their work in AI recruitment is relevant.",
    )

    assert message.recipient_name == "John Doe"
    assert len(message.message) >= 50


def test_short_recipient_name_rejected():
    with pytest.raises(ValidationError):
        OutreachMessage(
            recipient_name="J",
            message="This is a sufficiently long outreach message for testing purposes.",
            reason_for_outreach="Relevant professional background.",
        )


def test_short_message_rejected():
    with pytest.raises(ValidationError):
        OutreachMessage(
            recipient_name="John Doe",
            message="Too short",
            reason_for_outreach="Relevant professional background.",
        )


def test_short_reason_rejected():
    with pytest.raises(ValidationError):
        OutreachMessage(
            recipient_name="John Doe",
            message="This is a sufficiently long outreach message for testing purposes.",
            reason_for_outreach="Short",
        )


def test_long_reason_rejected():
    with pytest.raises(ValidationError):
        OutreachMessage(
            recipient_name="John Doe",
            message="This is a sufficiently long outreach message for testing purposes.",
            reason_for_outreach="A" * 201,
        )


# -------------------------
# BatchResponse
# -------------------------

def test_batch_response_default_is_empty():
    response = BatchResponse()

    assert response.results == []


def test_batch_response_with_results():
    message = OutreachMessage(
        recipient_name="John Doe",
        message=(
            "I noticed your recent work in AI recruitment and thought "
            "our platform could be relevant to the problems you're solving."
        ),
        reason_for_outreach="Their work in AI recruitment is relevant.",
    )

    response = BatchResponse(results=[message])

    assert len(response.results) == 1
    assert response.results[0].recipient_name == "John Doe"