import json

from google import genai

from app.config import settings
from app.models.response_models import OutreachMessage

client = genai.Client(api_key=settings.GOOGLE_API_KEY)


def generate_message(prompt: str) -> OutreachMessage:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type" : "application/json",
            
        }
    )

try:

    data = json.loads(response.text)

    return OutreachMessage.model_validate(data)

except Exception as e:
    raise ValueError(f"Failed to parse Gemini response: {e}")