from app.generator.message_builder import build_prompt
from app.generator.tone_templates import CASUAL
from app.llm.gemini_client import generate_message

prompt = build_prompt(
    profile_name="John Doe",
    headline="AI Engineer",
    about="Working on LLM-powered applications.",
    recent_activity=[
        "Shared a post about LangGraph.",
        "Published an article on RAG.",
    ],
    product_description="An AI tool that helps founders create personalized LinkedIn outreach.",
    tone_instruction=CASUAL,
)

message = generate_message(prompt)

print(message)