from google import genai
from app.config import settings

client = genai.Client(api_key=settings.GOOGLE_API_KEY)

def generate_message(prompt: str) -> str:
  response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
  )

  return response.text.strip()
