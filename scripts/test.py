from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

response = client.models.generate_content(
    model="gemini-3.1-flash-lite",
    contents="Say hello."
)

print(response.text)


"""
from fastapi import APIRouter, HTTPException

from app.agent.agent_core import generate_outreach
from app.models.request_models import OutreachRequest, BatchRequest
from app.models.response_models import OutreachMessage, BatchResponse

router = APIRouter(
    prefix="",
    tags=["Outreach"],
)


@router.post("/generate", response_model=OutreachMessage)
async def generate(request: OutreachRequest):
    try:
        return generate_outreach(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-batch", response_model=BatchResponse)
async def generate_batch(request: BatchRequest):
    results: list[OutreachMessage] = []

    for outreach_request in request.requests:
        try:
            result = generate_outreach(outreach_request)
            results.append(result)
        except Exception as e:
            print(
                f"Failed to process request for "
                f"{outreach_request.profile_url}: {e}"
            )
            continue

    return BatchResponse(results=results)

"""